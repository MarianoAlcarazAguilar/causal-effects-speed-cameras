"""
Cliente para la API de Google Places Aggregate.

Esta clase encapsula la funcionalidad de la API de Google Places Aggregate,
permitiendo obtener el conteo de negocios/lugares dentro de un área especificada.

Documentación oficial:
https://developers.google.com/maps/documentation/places-aggregate/overview
"""

import os
from typing import Optional, Literal, Any
from dataclasses import dataclass

import requests


# Tabla A completa de tipos de lugares válidos por categoría
# Referencia: https://developers.google.com/maps/documentation/places/web-service/place-types
# Los tipos marcados con (*) en la documentación original son tipos nuevos
PLACE_TYPES_BY_CATEGORY: dict[str, list[str]] = {
    "automotive": [
        "car_dealer",
        "car_rental",
        "car_repair",
        "car_wash",
        "electric_vehicle_charging_station",
        "gas_station",
        "parking",
        "rest_stop",
    ],
    "business": [
        "corporate_office",
        "farm",
        "ranch",
    ],
    "culture": [
        "art_gallery",
        "art_studio",
        "auditorium",
        "cultural_landmark",
        "historical_place",
        "monument",
        "museum",
        "performing_arts_theater",
        "sculpture",
    ],
    "education": [
        "library",
        "preschool",
        "primary_school",
        "school",
        "secondary_school",
        "university",
    ],
    "entertainment_and_recreation": [
        "adventure_sports_center",
        "amphitheatre",
        "amusement_center",
        "amusement_park",
        "aquarium",
        "banquet_hall",
        "barbecue_area",
        "botanical_garden",
        "bowling_alley",
        "casino",
        "childrens_camp",
        "comedy_club",
        "community_center",
        "concert_hall",
        "convention_center",
        "cultural_center",
        "cycling_park",
        "dance_hall",
        "dog_park",
        "event_venue",
        "ferris_wheel",
        "garden",
        "hiking_area",
        "historical_landmark",
        "internet_cafe",
        "karaoke",
        "marina",
        "movie_rental",
        "movie_theater",
        "national_park",
        "night_club",
        "observation_deck",
        "off_roading_area",
        "opera_house",
        "park",
        "philharmonic_hall",
        "picnic_ground",
        "planetarium",
        "plaza",
        "roller_coaster",
        "skateboard_park",
        "state_park",
        "tourist_attraction",
        "video_arcade",
        "visitor_center",
        "water_park",
        "wedding_venue",
        "wildlife_park",
        "wildlife_refuge",
        "zoo",
    ],
    "facilities": [
        "public_bath",
        "public_bathroom",
        "stable",
    ],
    "finance": [
        "accounting",
        "atm",
        "bank",
    ],
    "food_and_drink": [
        "acai_shop",
        "afghani_restaurant",
        "african_restaurant",
        "american_restaurant",
        "asian_restaurant",
        "bagel_shop",
        "bakery",
        "bar",
        "bar_and_grill",
        "barbecue_restaurant",
        "brazilian_restaurant",
        "breakfast_restaurant",
        "brunch_restaurant",
        "buffet_restaurant",
        "cafe",
        "cafeteria",
        "candy_store",
        "cat_cafe",
        "chinese_restaurant",
        "chocolate_factory",
        "chocolate_shop",
        "coffee_shop",
        "confectionery",
        "deli",
        "dessert_restaurant",
        "dessert_shop",
        "diner",
        "dog_cafe",
        "donut_shop",
        "fast_food_restaurant",
        "fine_dining_restaurant",
        "food_court",
        "french_restaurant",
        "greek_restaurant",
        "hamburger_restaurant",
        "ice_cream_shop",
        "indian_restaurant",
        "indonesian_restaurant",
        "italian_restaurant",
        "japanese_restaurant",
        "juice_shop",
        "korean_restaurant",
        "lebanese_restaurant",
        "meal_delivery",
        "meal_takeaway",
        "mediterranean_restaurant",
        "mexican_restaurant",
        "middle_eastern_restaurant",
        "pizza_restaurant",
        "pub",
        "ramen_restaurant",
        "restaurant",
        "sandwich_shop",
        "seafood_restaurant",
        "spanish_restaurant",
        "steak_house",
        "sushi_restaurant",
        "tea_house",
        "thai_restaurant",
        "turkish_restaurant",
        "vegan_restaurant",
        "vegetarian_restaurant",
        "vietnamese_restaurant",
        "wine_bar",
    ],
    "geographical_areas": [
        "administrative_area_level_1",
        "administrative_area_level_2",
        "country",
        "locality",
        "postal_code",
        "school_district",
    ],
    "government": [
        "city_hall",
        "courthouse",
        "embassy",
        "fire_station",
        "government_office",
        "local_government_office",
        "police",
        "post_office",
    ],
    "health_and_wellness": [
        "chiropractor",
        "dental_clinic",
        "dentist",
        "doctor",
        "drugstore",
        "hospital",
        "massage",
        "medical_lab",
        "pharmacy",
        "physiotherapist",
        "sauna",
        "skin_care_clinic",
        "spa",
        "tanning_studio",
        "wellness_center",
        "yoga_studio",
    ],
    "housing": [
        "apartment_building",
        "apartment_complex",
        "condominium_complex",
        "housing_complex",
    ],
    "lodging": [
        "bed_and_breakfast",
        "budget_japanese_inn",
        "campground",
        "camping_cabin",
        "cottage",
        "extended_stay_hotel",
        "farmstay",
        "guest_house",
        "hostel",
        "hotel",
        "inn",
        "japanese_inn",
        "lodging",
        "mobile_home_park",
        "motel",
        "private_guest_room",
        "resort_hotel",
        "rv_park",
    ],
    "natural_features": [
        "beach",
    ],
    "places_of_worship": [
        "church",
        "hindu_temple",
        "mosque",
        "synagogue",
    ],
    "services": [
        "astrologer",
        "barber_shop",
        "beautician",
        "beauty_salon",
        "body_art_service",
        "catering_service",
        "cemetery",
        "child_care_agency",
        "consultant",
        "courier_service",
        "electrician",
        "florist",
        "food_delivery",
        "foot_care",
        "funeral_home",
        "hair_care",
        "hair_salon",
        "insurance_agency",
        "laundry",
        "lawyer",
        "locksmith",
        "makeup_artist",
        "moving_company",
        "nail_salon",
        "painter",
        "plumber",
        "psychic",
        "real_estate_agency",
        "roofing_contractor",
        "storage",
        "summer_camp_organizer",
        "tailor",
        "telecommunications_service_provider",
        "tour_agency",
        "tourist_information_center",
        "travel_agency",
        "veterinary_care",
    ],
    "shopping": [
        "asian_grocery_store",
        "auto_parts_store",
        "bicycle_store",
        "book_store",
        "butcher_shop",
        "cell_phone_store",
        "clothing_store",
        "convenience_store",
        "department_store",
        "discount_store",
        "electronics_store",
        "food_store",
        "furniture_store",
        "gift_shop",
        "grocery_store",
        "hardware_store",
        "home_goods_store",
        "home_improvement_store",
        "jewelry_store",
        "liquor_store",
        "market",
        "pet_store",
        "shoe_store",
        "shopping_mall",
        "sporting_goods_store",
        "store",
        "supermarket",
        "warehouse_store",
        "wholesaler",
    ],
    "sports": [
        "arena",
        "athletic_field",
        "fishing_charter",
        "fishing_pond",
        "fitness_center",
        "golf_course",
        "gym",
        "ice_skating_rink",
        "playground",
        "ski_resort",
        "sports_activity_location",
        "sports_club",
        "sports_coaching",
        "sports_complex",
        "stadium",
        "swimming_pool",
    ],
    "transportation": [
        "airport",
        "airstrip",
        "bus_station",
        "bus_stop",
        "ferry_terminal",
        "heliport",
        "international_airport",
        "light_rail_station",
        "park_and_ride",
        "subway_station",
        "taxi_stand",
        "train_station",
        "transit_depot",
        "transit_station",
        "truck_stop",
    ],
}

# Set de todos los tipos válidos para validación rápida
ALL_VALID_PLACE_TYPES: set[str] = {
    place_type
    for types in PLACE_TYPES_BY_CATEGORY.values()
    for place_type in types
}


def get_place_types_by_category(category: str) -> list[str]:
    """
    Obtiene la lista de tipos de lugares para una categoría específica.
    
    Parameters
    ----------
    category : str
        Nombre de la categoría (e.g., 'food_and_drink', 'shopping', 'transportation').
    
    Returns
    -------
    list[str]
        Lista de tipos de lugares válidos para esa categoría.
    
    Raises
    ------
    ValueError
        Si la categoría no existe.
    
    Examples
    --------
    >>> get_place_types_by_category('finance')
    ['accounting', 'atm', 'bank']
    """
    if category not in PLACE_TYPES_BY_CATEGORY:
        valid_categories = list(PLACE_TYPES_BY_CATEGORY.keys())
        raise ValueError(
            f"Categoría '{category}' no válida. "
            f"Categorías válidas: {valid_categories}"
        )
    return PLACE_TYPES_BY_CATEGORY[category]


def get_all_categories() -> list[str]:
    """
    Obtiene la lista de todas las categorías disponibles.
    
    Returns
    -------
    list[str]
        Lista de nombres de categorías.
    
    Examples
    --------
    >>> categories = get_all_categories()
    >>> print(categories)
    ['automotive', 'business', 'culture', ...]
    """
    return list(PLACE_TYPES_BY_CATEGORY.keys())


def is_valid_place_type(place_type: str) -> bool:
    """
    Verifica si un tipo de lugar es válido.
    
    Parameters
    ----------
    place_type : str
        Tipo de lugar a verificar.
    
    Returns
    -------
    bool
        True si el tipo es válido, False en caso contrario.
    
    Examples
    --------
    >>> is_valid_place_type('restaurant')
    True
    >>> is_valid_place_type('invalid_type')
    False
    """
    return place_type in ALL_VALID_PLACE_TYPES


def validate_place_types(place_types: list[str]) -> tuple[list[str], list[str]]:
    """
    Valida una lista de tipos de lugares y separa válidos de inválidos.
    
    Parameters
    ----------
    place_types : list[str]
        Lista de tipos de lugares a validar.
    
    Returns
    -------
    tuple[list[str], list[str]]
        Tupla con (tipos_válidos, tipos_inválidos).
    
    Examples
    --------
    >>> valid, invalid = validate_place_types(['restaurant', 'invalid', 'bank'])
    >>> print(valid)
    ['restaurant', 'bank']
    >>> print(invalid)
    ['invalid']
    """
    valid = [t for t in place_types if t in ALL_VALID_PLACE_TYPES]
    invalid = [t for t in place_types if t not in ALL_VALID_PLACE_TYPES]
    return valid, invalid


def search_place_types(query: str) -> list[str]:
    """
    Busca tipos de lugares que contengan el texto especificado.
    
    Parameters
    ----------
    query : str
        Texto a buscar en los nombres de tipos de lugares.
    
    Returns
    -------
    list[str]
        Lista de tipos de lugares que coinciden con la búsqueda.
    
    Examples
    --------
    >>> search_place_types('restaurant')
    ['american_restaurant', 'barbecue_restaurant', 'brazilian_restaurant', ...]
    """
    query_lower = query.lower()
    return [t for t in ALL_VALID_PLACE_TYPES if query_lower in t.lower()]


@dataclass
class PlacesAggregateResponse:
    """
    Respuesta de la API de Places Aggregate.
    
    Attributes
    ----------
    count : int
        Número de lugares que coinciden con los criterios de búsqueda.
    place_ids : list[str]
        Lista de Place IDs (solo disponible si count <= 100).
    """
    count: int
    place_ids: list[str]


class InvalidPlaceTypeError(ValueError):
    """Error lanzado cuando se usa un tipo de lugar inválido."""
    
    def __init__(self, invalid_types: list[str]):
        self.invalid_types = invalid_types
        super().__init__(
            f"Tipos de lugar inválidos: {invalid_types}. "
            f"Use is_valid_place_type() o search_place_types() para encontrar tipos válidos."
        )


class GooglePlacesAggregate:
    """
    Cliente para la API de Google Places Aggregate.
    
    Esta clase permite obtener el número de negocios/lugares dentro de un área
    circular especificada, con opciones de filtrado por tipo de lugar, nivel de
    precios, calificación, y estado operacional.
    
    Parameters
    ----------
    api_key : str, optional
        Clave de API de Google Maps Platform. Si no se proporciona, se intenta
        leer de la variable de entorno GOOGLE_MAPS_API_KEY.
    
    Examples
    --------
    >>> client = GooglePlacesAggregate(api_key="your_api_key")
    >>> response = client.get_places_count(
    ...     latitude=19.4326,
    ...     longitude=-99.1332,
    ...     radius_m=500,
    ...     place_types=["restaurant", "cafe"]
    ... )
    >>> print(f"Found {response.count} places")
    
    Notes
    -----
    La API tiene las siguientes consideraciones:
    - Los Place IDs solo se devuelven si el conteo es <= 100
    - Se requiere una clave de API válida con el servicio Places Aggregate habilitado
    """
    
    BASE_URL = "https://areainsights.googleapis.com/v1:computeInsights"
    
    # Subconjunto de tipos comunes para análisis urbano (todos validados)
    DEFAULT_BUSINESS_TYPES = [
        # Food and Drink
        "restaurant",
        "cafe",
        # Shopping
        "shopping_mall",
        "supermarket",
        "convenience_store",
        "grocery_store",
        "store",
        # Automotive
        "gas_station",
        # Finance
        "bank",
        "atm",
        # Health
        "hospital",
        "pharmacy",
        # Education
        "school",
        # Entertainment
        "gym",
        "night_club",
        # Transportation
        "transit_station",
        "bus_station",
        "subway_station",
    ]
    
    def __init__(self, api_key: Optional[str] = None, validate_types: bool = True):
        """
        Inicializa el cliente de Google Places Aggregate.
        
        Parameters
        ----------
        api_key : str, optional
            Clave de API de Google Maps Platform.
        validate_types : bool, default=True
            Si es True, valida que los tipos de lugares sean válidos antes de
            hacer la solicitud. Si es False, permite cualquier tipo (útil si
            Google agrega nuevos tipos que aún no están en la lista).
        """
        self.api_key = api_key or os.environ.get("GOOGLE_MAPS_API_KEY")
        self.validate_types = validate_types
        if not self.api_key:
            raise ValueError(
                "API key is required. Provide it as a parameter or set "
                "the GOOGLE_MAPS_API_KEY environment variable."
            )
    
    def get_places_count(
        self,
        latitude: float,
        longitude: float,
        radius_m: float,
        place_types: Optional[list[str]] = DEFAULT_BUSINESS_TYPES,
        min_rating: Optional[float] = None,
        max_rating: Optional[float] = None,
        price_levels: Optional[list[str]] = None,
        operating_status: Optional[Literal["OPERATING_STATUS_OPERATIONAL", "OPERATING_STATUS_CLOSED_TEMPORARILY", "OPERATING_STATUS_CLOSED_PERMANENTLY"]] = None,
        include_place_ids: bool = False,
    ) -> PlacesAggregateResponse:
        """
        Obtiene el conteo de lugares dentro de un área circular.
        
        Parameters
        ----------
        latitude : float
            Latitud del centro del círculo (en grados decimales).
        longitude : float
            Longitud del centro del círculo (en grados decimales).
        radius_m : float
            Radio del círculo en metros.
        place_types : list[str], optional
            Lista de tipos de lugares a buscar. Ver BUSINESS_TYPES para ejemplos.
            Si no se especifica, se buscan todos los tipos.
        min_rating : float, optional
            Calificación mínima (1.0 - 5.0).
        max_rating : float, optional
            Calificación máxima (1.0 - 5.0).
        price_levels : list[str], optional
            Niveles de precio a incluir. Valores válidos:
            - "PRICE_LEVEL_FREE"
            - "PRICE_LEVEL_INEXPENSIVE"
            - "PRICE_LEVEL_MODERATE"
            - "PRICE_LEVEL_EXPENSIVE"
            - "PRICE_LEVEL_VERY_EXPENSIVE"
        operating_status : str, optional
            Estado operacional del lugar:
            - "OPERATING_STATUS_OPERATIONAL"
            - "OPERATING_STATUS_CLOSED_TEMPORARILY"
            - "OPERATING_STATUS_CLOSED_PERMANENTLY"
        include_place_ids : bool, default=False
            Si es True, solicita los Place IDs además del conteo.
            Solo se devuelven si el conteo es <= 100.
        
        Returns
        -------
        PlacesAggregateResponse
            Objeto con el conteo y opcionalmente los Place IDs.
        
        Raises
        ------
        requests.HTTPError
            Si la API devuelve un error HTTP.
        ValueError
            Si los parámetros son inválidos.
        
        Examples
        --------
        >>> response = client.get_places_count(
        ...     latitude=19.4326,
        ...     longitude=-99.1332,
        ...     radius_m=500,
        ...     place_types=["restaurant"],
        ...     min_rating=4.0,
        ...     operating_status="OPERATING_STATUS_OPERATIONAL"
        ... )
        """
        # Validar tipos de lugares si está habilitado
        if place_types and self.validate_types:
            valid, invalid = validate_place_types(place_types)
            if invalid:
                raise InvalidPlaceTypeError(invalid)
        
        # Construir el cuerpo de la solicitud
        request_body = self._build_request_body(
            latitude=latitude,
            longitude=longitude,
            radius_m=radius_m,
            place_types=place_types,
            min_rating=min_rating,
            max_rating=max_rating,
            price_levels=price_levels,
            operating_status=operating_status,
            include_place_ids=include_place_ids,
        )
        
        # Realizar la solicitud
        response = requests.post(
            self.BASE_URL,
            json=request_body,
            headers={
                "Content-Type": "application/json",
                "X-Goog-Api-Key": self.api_key,
            },
        )
        
        response.raise_for_status()
        
        return self._parse_response(response.json())
    
    def _build_request_body(
        self,
        latitude: float,
        longitude: float,
        radius_m: float,
        place_types: Optional[list[str]] = None,
        min_rating: Optional[float] = None,
        max_rating: Optional[float] = None,
        price_levels: Optional[list[str]] = None,
        operating_status: Optional[str] = None,
        include_place_ids: bool = False,
    ) -> dict:
        """
        Construye el cuerpo de la solicitud para la API.
        
        Parameters
        ----------
        latitude : float
            Latitud del centro.
        longitude : float
            Longitud del centro.
        radius_m : float
            Radio en metros.
        place_types : list[str], optional
            Tipos de lugares.
        min_rating : float, optional
            Calificación mínima.
        max_rating : float, optional
            Calificación máxima.
        price_levels : list[str], optional
            Niveles de precio.
        operating_status : str, optional
            Estado operacional.
        include_place_ids : bool
            Si incluir Place IDs.
        
        Returns
        -------
        dict
            Cuerpo de la solicitud en formato JSON.
        """
        # Definir los insights solicitados
        insights = ["INSIGHT_COUNT"]
        if include_place_ids:
            insights.append("INSIGHT_PLACES")
        
        request_body = {
            "insights": insights,
            "filter": {
                "locationFilter": {
                    "circle": {
                        "latLng": {
                            "latitude": latitude,
                            "longitude": longitude,
                        },
                        "radius": radius_m,
                    }
                }
            }
        }
        
        # Agregar filtro de tipos si se especifica
        if place_types:
            request_body["filter"]["typeFilter"] = {
                "includedTypes": place_types
            }
        
        # Agregar filtro de calificación si se especifica
        if min_rating is not None or max_rating is not None:
            rating_filter = {}
            if min_rating is not None:
                rating_filter["minRating"] = min_rating
            if max_rating is not None:
                rating_filter["maxRating"] = max_rating
            request_body["filter"]["ratingFilter"] = rating_filter
        
        # Agregar filtro de precio si se especifica
        if price_levels:
            request_body["filter"]["priceLevelFilter"] = {
                "priceLevels": price_levels
            }
        
        # Agregar filtro de estado operacional si se especifica
        if operating_status:
            request_body["filter"]["operatingStatusFilter"] = {
                "operatingStatuses": [operating_status]
            }
        
        return request_body
    
    def _parse_response(self, response_data: dict) -> PlacesAggregateResponse:
        """
        Parsea la respuesta de la API.
        
        Parameters
        ----------
        response_data : dict
            Datos JSON de la respuesta.
        
        Returns
        -------
        PlacesAggregateResponse
            Respuesta parseada.
        """
        try:
            count = int(response_data.get("count", 0))
        except ValueError:
            count = response_data.get("count", 0)
        place_ids = response_data.get("placeIds", [])
        
        return PlacesAggregateResponse(count=count, place_ids=place_ids)
    
    def get_business_density(
        self,
        latitude: float,
        longitude: float,
        radius_m: float,
        business_categories: Optional[list[str]] = None,
    ) -> dict[str, int]:
        """
        Obtiene la densidad de negocios por categoría dentro de un área.
        
        Este método es un helper que obtiene el conteo de diferentes tipos de
        negocios comúnmente utilizados en análisis urbano.
        
        Parameters
        ----------
        latitude : float
            Latitud del centro del círculo.
        longitude : float
            Longitud del centro del círculo.
        radius_m : float
            Radio del círculo en metros.
        business_categories : list[str], optional
            Lista de categorías a consultar. Si no se especifica, se usan
            las categorías en DEFAULT_BUSINESS_TYPES.
        
        Returns
        -------
        dict[str, int]
            Diccionario con el conteo de cada tipo de negocio.
        
        Examples
        --------
        >>> density = client.get_business_density(
        ...     latitude=19.4326,
        ...     longitude=-99.1332,
        ...     radius_m=500,
        ...     business_categories=["restaurant", "cafe", "bank"]
        ... )
        >>> print(density)
        {'restaurant': 15, 'cafe': 8, 'bank': 3}
        """
        categories = business_categories or self.DEFAULT_BUSINESS_TYPES
        density = {}
        
        for category in categories:
            try:
                response = self.get_places_count(
                    latitude=latitude,
                    longitude=longitude,
                    radius_m=radius_m,
                    place_types=[category],
                    operating_status="OPERATING_STATUS_OPERATIONAL",
                )
                density[category] = response.count
            except requests.HTTPError as e:
                # Log the error but continue with other categories
                print(f"Error getting business density for category {category}: {e}")
                density[category] = -1  # Indicate error
        
        return density


class GooglePlacesAggregateGRPC:
    """
    Cliente para la API de Google Places Aggregate usando gRPC.
    
    Esta clase encapsula la funcionalidad de la API de Google Places Aggregate
    mediante el cliente gRPC oficial, permitiendo obtener el conteo de negocios/lugares
    dentro de un área especificada con soporte para círculos, polígonos y regiones.
    
    Esta implementación requiere credenciales de cuenta de servicio (service account)
    en lugar de una API key.
    
    Documentación oficial:
    https://developers.google.com/maps/documentation/places-aggregate/example-requests?hl=es-419#python-grpc
    
    Parameters
    ----------
    service_account_path : str
        Ruta al archivo JSON de la cuenta de servicio de Google Cloud.
    scopes : list[str], optional
        Lista de scopes OAuth2. Por defecto usa el scope de cloud-platform.
    
    Examples
    --------
    >>> client = GooglePlacesAggregateGRPC(
    ...     service_account_path="path/to/service_account.json"
    ... )
    >>> response = client.get_places_count_circle(
    ...     latitude=19.4326,
    ...     longitude=-99.1332,
    ...     radius_m=500,
    ...     place_types=["restaurant", "cafe"]
    ... )
    >>> print(f"Found {response.count} places")
    
    Notes
    -----
    Requiere instalar las dependencias:
    - google-maps-areainsights
    - google-auth
    
    Instalación:
    pip install google-maps-areainsights google-auth
    """
    
    def __init__(
        self,
        service_account_path: str,
        scopes: Optional[list[str]] = None,
    ):
        """
        Inicializa el cliente gRPC de Google Places Aggregate.
        
        Parameters
        ----------
        service_account_path : str
            Ruta al archivo JSON de la cuenta de servicio.
        scopes : list[str], optional
            Scopes OAuth2. Por defecto: ['https://www.googleapis.com/auth/cloud-platform']
        """
        try:
            from google.maps import areainsights_v1
            from google.maps.areainsights_v1.types import (
                ComputeInsightsRequest,
                Filter,
                LocationFilter,
                TypeFilter,
                Insight,
                RatingFilter,
                OperatingStatus,
                PriceLevel,
            )
            from google.type import latlng_pb2
            from google.oauth2 import service_account
        except ImportError as e:
            raise ImportError(
                "Required packages not installed. Install with: "
                "pip install google-maps-areainsights google-auth"
            ) from e
        
        self.areainsights_v1 = areainsights_v1
        self.ComputeInsightsRequest = ComputeInsightsRequest
        self.Filter = Filter
        self.LocationFilter = LocationFilter
        self.TypeFilter = TypeFilter
        self.Insight = Insight
        self.RatingFilter = RatingFilter
        self.OperatingStatus = OperatingStatus
        self.PriceLevel = PriceLevel
        self.latlng_pb2 = latlng_pb2
        
        # Initialize credentials
        default_scopes = ['https://www.googleapis.com/auth/cloud-platform']
        scopes = scopes or default_scopes
        
        credentials = service_account.Credentials.from_service_account_file(
            service_account_path,
            scopes=scopes
        )
        
        # Initialize the client
        self.client = areainsights_v1.AreaInsightsClient(
            credentials=credentials
        )
    
    def get_places_count_circle(
        self,
        latitude: float,
        longitude: float,
        radius_m: float,
        place_types: Optional[list[str]] = None,
        min_rating: Optional[float] = None,
        max_rating: Optional[float] = None,
        price_levels: Optional[list[str]] = None,
        operating_status: Optional[list[str]] = None,
        include_place_ids: bool = False,
    ) -> PlacesAggregateResponse:
        """
        Obtiene el conteo de lugares dentro de un área circular.
        
        Parameters
        ----------
        latitude : float
            Latitud del centro del círculo (en grados decimales).
        longitude : float
            Longitud del centro del círculo (en grados decimales).
        radius_m : float
            Radio del círculo en metros.
        place_types : list[str], optional
            Lista de tipos de lugares a buscar.
        min_rating : float, optional
            Calificación mínima (1.0 - 5.0).
        max_rating : float, optional
            Calificación máxima (1.0 - 5.0).
        price_levels : list[str], optional
            Niveles de precio. Valores válidos:
            - "PRICE_LEVEL_FREE"
            - "PRICE_LEVEL_INEXPENSIVE"
            - "PRICE_LEVEL_MODERATE"
            - "PRICE_LEVEL_EXPENSIVE"
            - "PRICE_LEVEL_VERY_EXPENSIVE"
        operating_status : list[str], optional
            Estados operacionales. Valores válidos:
            - "OPERATING_STATUS_OPERATIONAL"
            - "OPERATING_STATUS_CLOSED_TEMPORARILY"
            - "OPERATING_STATUS_CLOSED_PERMANENTLY"
        include_place_ids : bool, default=False
            Si es True, solicita los Place IDs además del conteo.
            Solo se devuelven si el conteo es <= 100.
        
        Returns
        -------
        PlacesAggregateResponse
            Objeto con el conteo y opcionalmente los Place IDs.
        
        Examples
        --------
        >>> response = client.get_places_count_circle(
        ...     latitude=51.508,
        ...     longitude=-0.128,
        ...     radius_m=200,
        ...     place_types=["restaurant"],
        ...     min_rating=4.0
        ... )
        """
        # Create location filter with circle
        lat_lng = self.latlng_pb2.LatLng(
            latitude=latitude,
            longitude=longitude
        )
        
        location_filter = self.LocationFilter(
            circle=self.LocationFilter.Circle(
                lat_lng=lat_lng,
                radius=radius_m
            )
        )
        
        # Build filter
        filter_obj = self._build_filter(
            location_filter=location_filter,
            place_types=place_types,
            min_rating=min_rating,
            max_rating=max_rating,
            price_levels=price_levels,
            operating_status=operating_status,
        )
        
        # Build insights list
        insights = [self.Insight.INSIGHT_COUNT]
        if include_place_ids:
            insights.append(self.Insight.INSIGHT_PLACES)
        
        # Create the request
        request = self.ComputeInsightsRequest(
            insights=insights,
            filter=filter_obj
        )
        
        try:
            # Make the request
            response = self.client.compute_insights(request=request)
            
            # Parse response
            place_ids = []
            if hasattr(response, 'places') and response.places:
                place_ids = [place.id for place in response.places]
            
            return PlacesAggregateResponse(
                count=response.count,
                place_ids=place_ids
            )
        except Exception as e:
            raise RuntimeError(f"Error calling Places Aggregate API: {e}") from e
    
    def get_places_count_polygon(
        self,
        coordinates: list[tuple[float, float]],
        place_types: Optional[list[str]] = None,
        min_rating: Optional[float] = None,
        max_rating: Optional[float] = None,
        price_levels: Optional[list[str]] = None,
        operating_status: Optional[list[str]] = None,
        include_place_ids: bool = False,
    ) -> PlacesAggregateResponse:
        """
        Obtiene el conteo de lugares dentro de un polígono personalizado.
        
        Parameters
        ----------
        coordinates : list[tuple[float, float]]
            Lista de coordenadas (lat, lng) que definen el polígono.
            El primer punto debe repetirse al final para cerrar el polígono.
        place_types : list[str], optional
            Lista de tipos de lugares a buscar.
        min_rating : float, optional
            Calificación mínima (1.0 - 5.0).
        max_rating : float, optional
            Calificación máxima (1.0 - 5.0).
        price_levels : list[str], optional
            Niveles de precio a incluir.
        operating_status : list[str], optional
            Estados operacionales a incluir.
        include_place_ids : bool, default=False
            Si es True, solicita los Place IDs además del conteo.
        
        Returns
        -------
        PlacesAggregateResponse
            Objeto con el conteo y opcionalmente los Place IDs.
        
        Examples
        --------
        >>> coords = [
        ...     (37.776, -122.666),
        ...     (37.130, -121.898),
        ...     (37.326, -121.598),
        ...     (37.912, -122.247),
        ...     (37.776, -122.666)  # Closing point
        ... ]
        >>> response = client.get_places_count_polygon(
        ...     coordinates=coords,
        ...     place_types=["restaurant"]
        ... )
        """
        # Create coordinates for the polygon
        polygon_coords = [
            self.latlng_pb2.LatLng(latitude=lat, longitude=lng)
            for lat, lng in coordinates
        ]
        
        # Create custom area with polygon
        location_filter = self.LocationFilter(
            custom_area=self.LocationFilter.CustomArea(
                polygon=self.LocationFilter.CustomArea.Polygon(
                    coordinates=polygon_coords
                )
            )
        )
        
        # Build filter
        filter_obj = self._build_filter(
            location_filter=location_filter,
            place_types=place_types,
            min_rating=min_rating,
            max_rating=max_rating,
            price_levels=price_levels,
            operating_status=operating_status,
        )
        
        # Build insights list
        insights = [self.Insight.INSIGHT_COUNT]
        if include_place_ids:
            insights.append(self.Insight.INSIGHT_PLACES)
        
        # Create the request
        request = self.ComputeInsightsRequest(
            insights=insights,
            filter=filter_obj
        )
        
        try:
            # Make the request
            response = self.client.compute_insights(request=request)
            
            # Parse response
            place_ids = []
            if hasattr(response, 'places') and response.places:
                place_ids = [place.id for place in response.places]
            
            return PlacesAggregateResponse(
                count=response.count,
                place_ids=place_ids
            )
        except Exception as e:
            raise RuntimeError(f"Error calling Places Aggregate API: {e}") from e
    
    def get_places_count_region(
        self,
        place_id: str,
        place_types: Optional[list[str]] = None,
        min_rating: Optional[float] = None,
        max_rating: Optional[float] = None,
        price_levels: Optional[list[str]] = None,
        operating_status: Optional[list[str]] = None,
        include_place_ids: bool = False,
    ) -> PlacesAggregateResponse:
        """
        Obtiene el conteo de lugares dentro de una región geográfica usando un Place ID.
        
        Los Place IDs de áreas geográficas incluyen la geometría de un lugar, como una ciudad.
        Puedes obtener un Place ID de área geográfica de:
        - Buscador de ID de lugar
        - API de Geocoding
        - Text Search (nuevo)
        - Nearby Search (nuevo)
        - API de Address Validation
        - Place Autocomplete
        
        Parameters
        ----------
        place_id : str
            Place ID del área geográfica (formato: "places/ChIJ..." o solo "ChIJ...").
            Si no incluye el prefijo "places/", se agregará automáticamente.
        place_types : list[str], optional
            Lista de tipos de lugares a buscar.
        min_rating : float, optional
            Calificación mínima (1.0 - 5.0).
        max_rating : float, optional
            Calificación máxima (1.0 - 5.0).
        price_levels : list[str], optional
            Niveles de precio a incluir.
        operating_status : list[str], optional
            Estados operacionales a incluir.
        include_place_ids : bool, default=False
            Si es True, solicita los Place IDs además del conteo.
        
        Returns
        -------
        PlacesAggregateResponse
            Objeto con el conteo y opcionalmente los Place IDs.
        
        Examples
        --------
        >>> # Mountain View, California
        >>> response = client.get_places_count_region(
        ...     place_id="ChIJiQHsW0m3j4ARm69rRkrUF3w",
        ...     place_types=["restaurant"]
        ... )
        """
        # Ensure place_id has the "places/" prefix
        if not place_id.startswith("places/"):
            place_id = f"places/{place_id}"
        
        # Create location filter with region
        location_filter = self.LocationFilter(
            region=self.LocationFilter.Region(
                place=place_id
            )
        )
        
        # Build filter
        filter_obj = self._build_filter(
            location_filter=location_filter,
            place_types=place_types,
            min_rating=min_rating,
            max_rating=max_rating,
            price_levels=price_levels,
            operating_status=operating_status,
        )
        
        # Build insights list
        insights = [self.Insight.INSIGHT_COUNT]
        if include_place_ids:
            insights.append(self.Insight.INSIGHT_PLACES)
        
        # Create the request
        request = self.ComputeInsightsRequest(
            insights=insights,
            filter=filter_obj
        )
        
        try:
            # Make the request
            response = self.client.compute_insights(request=request)
            
            # Parse response
            place_ids = []
            if hasattr(response, 'places') and response.places:
                place_ids = [place.id for place in response.places]
            
            return PlacesAggregateResponse(
                count=response.count,
                place_ids=place_ids
            )
        except Exception as e:
            raise RuntimeError(f"Error calling Places Aggregate API: {e}") from e
    
    def _build_filter(
        self,
        location_filter: Any,
        place_types: Optional[list[str]] = None,
        min_rating: Optional[float] = None,
        max_rating: Optional[float] = None,
        price_levels: Optional[list[str]] = None,
        operating_status: Optional[list[str]] = None,
    ) -> Any:
        """
        Construye un objeto Filter con todos los filtros especificados.
        
        Parameters
        ----------
        location_filter : LocationFilter
            Filtro de ubicación (círculo, polígono o región).
        place_types : list[str], optional
            Tipos de lugares a incluir.
        min_rating : float, optional
            Calificación mínima.
        max_rating : float, optional
            Calificación máxima.
        price_levels : list[str], optional
            Niveles de precio.
        operating_status : list[str], optional
            Estados operacionales.
        
        Returns
        -------
        Filter
            Objeto Filter configurado.
        """
        # Create type filter if specified
        type_filter = None
        if place_types:
            type_filter = self.TypeFilter(
                included_types=place_types
            )
        
        # Create rating filter if specified
        rating_filter = None
        if min_rating is not None or max_rating is not None:
            rating_filter = self.RatingFilter()
            if min_rating is not None:
                rating_filter.min_rating = min_rating
            if max_rating is not None:
                rating_filter.max_rating = max_rating
        
        # Convert price level strings to enum values
        price_level_enums = None
        if price_levels:
            price_level_map = {
                "PRICE_LEVEL_FREE": self.PriceLevel.PRICE_LEVEL_FREE,
                "PRICE_LEVEL_INEXPENSIVE": self.PriceLevel.PRICE_LEVEL_INEXPENSIVE,
                "PRICE_LEVEL_MODERATE": self.PriceLevel.PRICE_LEVEL_MODERATE,
                "PRICE_LEVEL_EXPENSIVE": self.PriceLevel.PRICE_LEVEL_EXPENSIVE,
                "PRICE_LEVEL_VERY_EXPENSIVE": self.PriceLevel.PRICE_LEVEL_VERY_EXPENSIVE,
            }
            price_level_enums = [
                price_level_map[pl] for pl in price_levels
                if pl in price_level_map
            ]
        
        # Convert operating status strings to enum values
        operating_status_enums = None
        if operating_status:
            status_map = {
                "OPERATING_STATUS_OPERATIONAL": self.OperatingStatus.OPERATING_STATUS_OPERATIONAL,
                "OPERATING_STATUS_CLOSED_TEMPORARILY": self.OperatingStatus.OPERATING_STATUS_CLOSED_TEMPORARILY,
                "OPERATING_STATUS_CLOSED_PERMANENTLY": self.OperatingStatus.OPERATING_STATUS_CLOSED_PERMANENTLY,
            }
            operating_status_enums = [
                status_map[status] for status in operating_status
                if status in status_map
            ]
        
        # Build the filter
        filter_kwargs = {
            "location_filter": location_filter,
        }
        
        if type_filter:
            filter_kwargs["type_filter"] = type_filter
        
        if rating_filter:
            filter_kwargs["rating_filter"] = rating_filter
        
        if price_level_enums:
            filter_kwargs["price_levels"] = price_level_enums
        
        if operating_status_enums:
            filter_kwargs["operating_status"] = operating_status_enums
        
        return self.Filter(**filter_kwargs)


@dataclass
class Place:
    """
    Representa un lugar de la API de Places.
    
    Attributes
    ----------
    place_id : str
        ID único del lugar.
    display_name : str
        Nombre para mostrar del lugar.
    formatted_address : str
        Dirección formateada.
    location : tuple[float, float]
        Coordenadas (lat, lng).
    rating : float, optional
        Calificación del lugar.
    user_rating_count : int, optional
        Número de calificaciones.
    price_level : str, optional
        Nivel de precio.
    types : list[str]
        Tipos de lugar.
    """
    place_id: str
    display_name: str
    formatted_address: str
    location: tuple[float, float]
    rating: Optional[float] = None
    user_rating_count: Optional[int] = None
    price_level: Optional[str] = None
    types: list[str] = None
    
    def __post_init__(self):
        """Ensure types is always a list."""
        if self.types is None:
            self.types = []


@dataclass
class PlaceDetails:
    """
    Detalles completos de un lugar.
    
    Attributes
    ----------
    place_id : str
        ID único del lugar.
    display_name : str
        Nombre para mostrar.
    formatted_address : str
        Dirección formateada.
    location : tuple[float, float]
        Coordenadas (lat, lng).
    rating : float, optional
        Calificación.
    user_rating_count : int, optional
        Número de calificaciones.
    price_level : str, optional
        Nivel de precio.
    phone_number : str, optional
        Número de teléfono.
    website_uri : str, optional
        URI del sitio web.
    business_status : str, optional
        Estado del negocio.
    """
    place_id: str
    display_name: str
    formatted_address: str
    location: tuple[float, float]
    rating: Optional[float] = None
    user_rating_count: Optional[int] = None
    price_level: Optional[str] = None
    phone_number: Optional[str] = None
    website_uri: Optional[str] = None
    business_status: Optional[str] = None


@dataclass
class PlaceSearchResponse:
    """
    Respuesta de búsqueda de lugares.
    
    Attributes
    ----------
    places : list[Place]
        Lista de lugares encontrados.
    next_page_token : str, optional
        Token para la siguiente página de resultados.
    """
    places: list[Place]
    next_page_token: Optional[str] = None


class GooglePlacesAPI:
    """
    Cliente para la API de Google Places (web service).
    
    Esta clase encapsula la funcionalidad de la API de Places mediante el cliente
    gRPC oficial, permitiendo realizar búsquedas de texto, búsquedas cercanas,
    obtener detalles de lugares, fotos y autocompletado.
    
    Esta implementación requiere credenciales de cuenta de servicio (service account)
    en lugar de una API key.
    
    Documentación oficial:
    https://developers.google.com/maps/documentation/places/web-service
    
    Parameters
    ----------
    service_account_path : str
        Ruta al archivo JSON de la cuenta de servicio de Google Cloud.
    scopes : list[str], optional
        Lista de scopes OAuth2. Por defecto usa el scope de cloud-platform.
    
    Examples
    --------
    >>> client = GooglePlacesAPI(
    ...     service_account_path="path/to/service_account.json"
    ... )
    >>> # Text search
    >>> results = client.text_search(
    ...     text_query="restaurants in Mexico City",
    ...     location_bias_lat=19.4326,
    ...     location_bias_lng=-99.1332,
    ...     location_bias_radius=5000
    ... )
    >>> for place in results.places:
    ...     print(f"{place.display_name}: {place.rating}")
    
    Notes
    -----
    Requiere instalar las dependencias:
    - google-maps-places
    - google-auth
    
    Instalación:
    pip install google-maps-places google-auth
    """
    
    def __init__(
        self,
        service_account_path: str,
        scopes: Optional[list[str]] = None,
    ):
        """
        Inicializa el cliente gRPC de Google Places API.
        
        Parameters
        ----------
        service_account_path : str
            Ruta al archivo JSON de la cuenta de servicio.
        scopes : list[str], optional
            Scopes OAuth2. Por defecto: ['https://www.googleapis.com/auth/cloud-platform']
        """
        try:
            from google.maps import places_v1
            from google.maps.places_v1.types import (
                SearchTextRequest,
                SearchNearbyRequest,
                GetPlaceRequest,
                GetPhotoMediaRequest,
                AutocompletePlacesRequest,
            )
            from google.type import latlng_pb2
            from google.oauth2 import service_account
        except ImportError as e:
            raise ImportError(
                "Required packages not installed. Install with: "
                "pip install google-maps-places google-auth"
            ) from e
        
        self.places_v1 = places_v1
        self.SearchTextRequest = SearchTextRequest
        self.SearchNearbyRequest = SearchNearbyRequest
        self.GetPlaceRequest = GetPlaceRequest
        self.GetPhotoMediaRequest = GetPhotoMediaRequest
        self.AutocompletePlacesRequest = AutocompletePlacesRequest
        self.latlng_pb2 = latlng_pb2
        
        # Initialize credentials
        default_scopes = ['https://www.googleapis.com/auth/cloud-platform']
        scopes = scopes or default_scopes
        
        credentials = service_account.Credentials.from_service_account_file(
            service_account_path,
            scopes=scopes
        )
        
        # Initialize the client (async client, but we'll use sync methods)
        self.client = self.places_v1.PlacesClient(
            credentials=credentials
        )
    
    def text_search(
        self,
        text_query: str,
        location_bias_lat: Optional[float] = None,
        location_bias_lng: Optional[float] = None,
        location_bias_radius: Optional[float] = None,
        min_rating: Optional[float] = None,
        max_rating: Optional[float] = None,
        price_levels: Optional[list[str]] = None,
        open_now: bool = False,
        language_code: Optional[str] = None,
        region_code: Optional[str] = None,
        included_types: Optional[list[str]] = None,
        excluded_types: Optional[list[str]] = None,
    ) -> PlaceSearchResponse:
        """
        Busca lugares usando una consulta de texto.
        
        Parameters
        ----------
        text_query : str
            Consulta de búsqueda de texto (ej: "restaurants in Mexico City").
        location_bias_lat : float, optional
            Latitud para sesgo de ubicación circular.
        location_bias_lng : float, optional
            Longitud para sesgo de ubicación circular.
        location_bias_radius : float, optional
            Radio en metros para sesgo de ubicación circular.
        min_rating : float, optional
            Calificación mínima (1.0 - 5.0).
        max_rating : float, optional
            Calificación máxima (1.0 - 5.0).
        price_levels : list[str], optional
            Niveles de precio a incluir.
        open_now : bool, default=False
            Si es True, solo devuelve lugares abiertos ahora.
        language_code : str, optional
            Código de idioma para las respuestas (ej: "es", "en").
        region_code : str, optional
            Código de región para sesgo de resultados (ej: "MX", "US").
        included_types : list[str], optional
            Tipos de lugares a incluir.
        excluded_types : list[str], optional
            Tipos de lugares a excluir.
        
        Returns
        -------
        PlaceSearchResponse
            Respuesta con lugares encontrados y token de paginación.
        
        Examples
        --------
        >>> results = client.text_search(
        ...     text_query="restaurants with terrace",
        ...     location_bias_lat=51.516177,
        ...     location_bias_lng=-0.127245,
        ...     location_bias_radius=1000,
        ...     min_rating=4.0,
        ...     open_now=True
        ... )
        """
        # Build location bias if provided
        location_bias = None
        if location_bias_lat is not None and location_bias_lng is not None and location_bias_radius is not None:
            center_point = self.latlng_pb2.LatLng(
                latitude=location_bias_lat,
                longitude=location_bias_lng
            )
            circle_area = self.places_v1.types.Circle(
                center=center_point,
                radius=location_bias_radius
            )
            location_bias = self.SearchTextRequest.LocationBias(
                circle=circle_area
            )
        
        # Build request
        request_kwargs = {
            "text_query": text_query,
        }
        
        if location_bias:
            request_kwargs["location_bias"] = location_bias
        
        if min_rating is not None:
            request_kwargs["min_rating"] = min_rating
        
        if max_rating is not None:
            request_kwargs["max_rating"] = max_rating
        
        if open_now:
            request_kwargs["open_now"] = True
        
        if language_code:
            request_kwargs["language_code"] = language_code
        
        if region_code:
            request_kwargs["region_code"] = region_code
        
        if included_types:
            request_kwargs["included_type"] = included_types[0] if len(included_types) == 1 else None
            if len(included_types) > 1:
                # Note: API typically supports one included_type, but we can try multiple
                request_kwargs["included_types"] = included_types
        
        if excluded_types:
            request_kwargs["excluded_types"] = excluded_types
        
        if price_levels:
            # Convert price level strings to enum values
            price_level_map = {
                "PRICE_LEVEL_FREE": self.places_v1.types.PriceLevel.PRICE_LEVEL_FREE,
                "PRICE_LEVEL_INEXPENSIVE": self.places_v1.types.PriceLevel.PRICE_LEVEL_INEXPENSIVE,
                "PRICE_LEVEL_MODERATE": self.places_v1.types.PriceLevel.PRICE_LEVEL_MODERATE,
                "PRICE_LEVEL_EXPENSIVE": self.places_v1.types.PriceLevel.PRICE_LEVEL_EXPENSIVE,
                "PRICE_LEVEL_VERY_EXPENSIVE": self.places_v1.types.PriceLevel.PRICE_LEVEL_VERY_EXPENSIVE,
            }
            price_level_enums = [
                price_level_map[pl] for pl in price_levels
                if pl in price_level_map
            ]
            if price_level_enums:
                request_kwargs["price_levels"] = price_level_enums
        
        request = self.SearchTextRequest(**request_kwargs)
        
        try:
            response = self.client.search_text(request=request)
            
            # Parse places
            places = []
            for place in response.places:
                places.append(self._parse_place(place))
            
            next_page_token = response.next_page_token if hasattr(response, 'next_page_token') else None
            
            return PlaceSearchResponse(
                places=places,
                next_page_token=next_page_token
            )
        except Exception as e:
            raise RuntimeError(f"Error calling Places API text search: {e}") from e
    
    def nearby_search(
        self,
        latitude: float,
        longitude: float,
        radius_m: Optional[float] = None,
        included_types: Optional[list[str]] = None,
        excluded_types: Optional[list[str]] = None,
        max_result_count: Optional[int] = None,
        language_code: Optional[str] = None,
        region_code: Optional[str] = None,
    ) -> PlaceSearchResponse:
        """
        Busca lugares cercanos a una ubicación específica.
        
        Parameters
        ----------
        latitude : float
            Latitud del punto de búsqueda.
        longitude : float
            Longitud del punto de búsqueda.
        radius_m : float, optional
            Radio de búsqueda en metros (máximo 50000).
        included_types : list[str], optional
            Tipos de lugares a incluir (al menos uno requerido).
        excluded_types : list[str], optional
            Tipos de lugares a excluir.
        max_result_count : int, optional
            Número máximo de resultados a devolver (máximo 20).
        language_code : str, optional
            Código de idioma para las respuestas.
        region_code : str, optional
            Código de región para sesgo de resultados.
        
        Returns
        -------
        PlaceSearchResponse
            Respuesta con lugares encontrados.
        
        Examples
        --------
        >>> results = client.nearby_search(
        ...     latitude=19.4326,
        ...     longitude=-99.1332,
        ...     radius_m=1000,
        ...     included_types=["restaurant", "cafe"]
        ... )
        """
        location = self.latlng_pb2.LatLng(
            latitude=latitude,
            longitude=longitude
        )
        
        request_kwargs = {
            "location_restriction": self.SearchNearbyRequest.LocationRestriction(
                circle=self.SearchNearbyRequest.LocationRestriction.Circle(
                    center=location,
                    radius=radius_m if radius_m else 50000
                )
            )
        }
        
        if included_types:
            request_kwargs["included_types"] = included_types
        
        if excluded_types:
            request_kwargs["excluded_types"] = excluded_types
        
        if max_result_count:
            request_kwargs["max_result_count"] = min(max_result_count, 20)
        
        if language_code:
            request_kwargs["language_code"] = language_code
        
        if region_code:
            request_kwargs["region_code"] = region_code
        
        request = self.SearchNearbyRequest(**request_kwargs)
        
        try:
            response = self.client.search_nearby(request=request)
            
            # Parse places
            places = []
            for place in response.places:
                places.append(self._parse_place(place))
            
            return PlaceSearchResponse(places=places)
        except Exception as e:
            raise RuntimeError(f"Error calling Places API nearby search: {e}") from e
    
    def get_place_details(
        self,
        place_id: str,
        language_code: Optional[str] = None,
        region_code: Optional[str] = None,
    ) -> PlaceDetails:
        """
        Obtiene detalles completos de un lugar específico.
        
        Parameters
        ----------
        place_id : str
            Place ID del lugar (formato: "places/ChIJ..." o solo "ChIJ...").
        language_code : str, optional
            Código de idioma para las respuestas.
        region_code : str, optional
            Código de región para sesgo de resultados.
        
        Returns
        -------
        PlaceDetails
            Detalles completos del lugar.
        
        Examples
        --------
        >>> details = client.get_place_details(
        ...     place_id="ChIJN1t_tDeuEmsRUsoyG83frY4",
        ...     language_code="es"
        ... )
        >>> print(f"{details.display_name}: {details.phone_number}")
        """
        # Ensure place_id has the "places/" prefix
        if not place_id.startswith("places/"):
            place_id = f"places/{place_id}"
        
        request_kwargs = {
            "name": place_id,
        }
        
        if language_code:
            request_kwargs["language_code"] = language_code
        
        if region_code:
            request_kwargs["region_code"] = region_code
        
        request = self.GetPlaceRequest(**request_kwargs)
        
        try:
            response = self.client.get_place(request=request)
            place = response
            
            # Extract location
            location = None
            if hasattr(place, 'location') and place.location:
                location = (place.location.latitude, place.location.longitude)
            
            # Extract display name
            display_name = ""
            if hasattr(place, 'display_name') and place.display_name:
                display_name = place.display_name.text if hasattr(place.display_name, 'text') else str(place.display_name)
            
            # Extract formatted address
            formatted_address = ""
            if hasattr(place, 'formatted_address'):
                formatted_address = place.formatted_address
            
            # Extract rating
            rating = None
            if hasattr(place, 'rating'):
                rating = place.rating
            
            # Extract user rating count
            user_rating_count = None
            if hasattr(place, 'user_rating_count'):
                user_rating_count = place.user_rating_count
            
            # Extract price level
            price_level = None
            if hasattr(place, 'price_level'):
                price_level = str(place.price_level) if place.price_level else None
            
            # Extract phone number
            phone_number = None
            if hasattr(place, 'national_phone_number'):
                phone_number = place.national_phone_number
            elif hasattr(place, 'international_phone_number'):
                phone_number = place.international_phone_number
            
            # Extract website
            website_uri = None
            if hasattr(place, 'website_uri'):
                website_uri = place.website_uri
            
            # Extract business status
            business_status = None
            if hasattr(place, 'business_status'):
                business_status = str(place.business_status) if place.business_status else None
            
            return PlaceDetails(
                place_id=place.id if hasattr(place, 'id') else place_id,
                display_name=display_name,
                formatted_address=formatted_address,
                location=location or (0.0, 0.0),
                rating=rating,
                user_rating_count=user_rating_count,
                price_level=price_level,
                phone_number=phone_number,
                website_uri=website_uri,
                business_status=business_status
            )
        except Exception as e:
            raise RuntimeError(f"Error calling Places API get place details: {e}") from e
    
    def get_place_photo(
        self,
        photo_reference: str,
        max_width_px: Optional[int] = None,
        max_height_px: Optional[int] = None,
        skip_http_redirect: bool = False,
    ) -> str:
        """
        Obtiene la URL o datos de una foto de un lugar.
        
        Parameters
        ----------
        photo_reference : str
            Referencia de la foto (obtenida de place details o search results).
        max_width_px : int, optional
            Ancho máximo de la imagen en píxeles.
        max_height_px : int, optional
            Alto máximo de la imagen en píxeles.
        skip_http_redirect : bool, default=False
            Si es True, devuelve la URL directamente sin seguir redirecciones.
        
        Returns
        -------
        str
            URL de la foto o URI de los datos de la foto.
        
        Examples
        --------
        >>> photo_url = client.get_place_photo(
        ...     photo_reference="photo_ref_from_place_details",
        ...     max_width_px=800
        ... )
        """
        # Ensure photo_reference has the "places/" prefix if needed
        if not photo_reference.startswith("places/"):
            photo_ref_name = f"places/{photo_reference}"
        else:
            photo_ref_name = photo_reference
        
        request_kwargs = {
            "name": photo_ref_name,
        }
        
        if max_width_px:
            request_kwargs["max_width_px"] = max_width_px
        
        if max_height_px:
            request_kwargs["max_height_px"] = max_height_px
        
        if skip_http_redirect:
            request_kwargs["skip_http_redirect"] = True
        
        request = self.GetPhotoMediaRequest(**request_kwargs)
        
        try:
            response = self.client.get_photo_media(request=request)
            
            # Extract photo URI
            if hasattr(response, 'photo_uri'):
                return response.photo_uri
            elif hasattr(response, 'name'):
                return response.name
            else:
                return str(response)
        except Exception as e:
            raise RuntimeError(f"Error calling Places API get photo: {e}") from e
    
    def autocomplete(
        self,
        input_text: str,
        location_bias_lat: Optional[float] = None,
        location_bias_lng: Optional[float] = None,
        location_bias_radius: Optional[float] = None,
        language_code: Optional[str] = None,
        region_code: Optional[str] = None,
        included_primary_types: Optional[list[str]] = None,
        included_region_codes: Optional[list[str]] = None,
    ) -> list[Place]:
        """
        Obtiene predicciones de autocompletado para lugares.
        
        Parameters
        ----------
        input_text : str
            Texto de entrada para autocompletar.
        location_bias_lat : float, optional
            Latitud para sesgo de ubicación circular.
        location_bias_lng : float, optional
            Longitud para sesgo de ubicación circular.
        location_bias_radius : float, optional
            Radio en metros para sesgo de ubicación circular.
        language_code : str, optional
            Código de idioma para las respuestas.
        region_code : str, optional
            Código de región para sesgo de resultados.
        included_primary_types : list[str], optional
            Tipos primarios de lugares a incluir.
        included_region_codes : list[str], optional
            Códigos de región a incluir.
        
        Returns
        -------
        list[Place]
            Lista de predicciones de lugares.
        
        Examples
        --------
        >>> predictions = client.autocomplete(
        ...     input_text="restaurants in",
        ...     location_bias_lat=19.4326,
        ...     location_bias_lng=-99.1332,
        ...     location_bias_radius=5000
        ... )
        >>> for place in predictions:
        ...     print(place.display_name)
        """
        # Build location bias if provided
        location_bias = None
        if location_bias_lat is not None and location_bias_lng is not None and location_bias_radius is not None:
            center_point = self.latlng_pb2.LatLng(
                latitude=location_bias_lat,
                longitude=location_bias_lng
            )
            circle_area = self.places_v1.types.Circle(
                center=center_point,
                radius=location_bias_radius
            )
            location_bias = self.AutocompletePlacesRequest.LocationBias(
                circle=circle_area
            )
        
        request_kwargs = {
            "input": input_text,
        }
        
        if location_bias:
            request_kwargs["location_bias"] = location_bias
        
        if language_code:
            request_kwargs["language_code"] = language_code
        
        if region_code:
            request_kwargs["region_code"] = region_code
        
        if included_primary_types:
            request_kwargs["included_primary_types"] = included_primary_types
        
        if included_region_codes:
            request_kwargs["included_region_codes"] = included_region_codes
        
        request = self.AutocompletePlacesRequest(**request_kwargs)
        
        try:
            response = self.client.autocomplete_places(request=request)
            
            # Parse suggestions
            places = []
            if hasattr(response, 'suggestions'):
                for suggestion in response.suggestions:
                    if hasattr(suggestion, 'place_prediction') and suggestion.place_prediction:
                        pred = suggestion.place_prediction
                        place_id = pred.place_id if hasattr(pred, 'place_id') else ""
                        display_name = pred.text.text if hasattr(pred, 'text') and hasattr(pred.text, 'text') else ""
                        
                        # Try to get location from structured_format
                        location = (0.0, 0.0)
                        if hasattr(pred, 'structured_format'):
                            # Location might be in structured_format, but typically not available in autocomplete
                            pass
                        
                        places.append(Place(
                            place_id=place_id,
                            display_name=display_name,
                            formatted_address="",  # Not available in autocomplete
                            location=location,
                            types=pred.types if hasattr(pred, 'types') else []
                        ))
            
            return places
        except Exception as e:
            raise RuntimeError(f"Error calling Places API autocomplete: {e}") from e
    
    def _parse_place(self, place: Any) -> Place:
        """
        Parsea un objeto Place de la API a nuestro dataclass Place.
        
        Parameters
        ----------
        place : Any
            Objeto Place de la API gRPC.
        
        Returns
        -------
        Place
            Objeto Place parseado.
        """
        # Extract place ID
        place_id = place.id if hasattr(place, 'id') else ""
        
        # Extract display name
        display_name = ""
        if hasattr(place, 'display_name') and place.display_name:
            display_name = place.display_name.text if hasattr(place.display_name, 'text') else str(place.display_name)
        
        # Extract formatted address
        formatted_address = ""
        if hasattr(place, 'formatted_address'):
            formatted_address = place.formatted_address
        
        # Extract location
        location = (0.0, 0.0)
        if hasattr(place, 'location') and place.location:
            location = (place.location.latitude, place.location.longitude)
        
        # Extract rating
        rating = None
        if hasattr(place, 'rating'):
            rating = place.rating
        
        # Extract user rating count
        user_rating_count = None
        if hasattr(place, 'user_rating_count'):
            user_rating_count = place.user_rating_count
        
        # Extract price level
        price_level = None
        if hasattr(place, 'price_level'):
            price_level = str(place.price_level) if place.price_level else None
        
        # Extract types
        types = []
        if hasattr(place, 'types'):
            types = list(place.types) if place.types else []
        
        return Place(
            place_id=place_id,
            display_name=display_name,
            formatted_address=formatted_address,
            location=location,
            rating=rating,
            user_rating_count=user_rating_count,
            price_level=price_level,
            types=types or []
        )
