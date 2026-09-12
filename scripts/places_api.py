"""
Google Places API (New) Python Client

This module provides a Python class to interact with the Google Places API (New).
Supports all major endpoints: Nearby Search, Text Search, Place Details, 
Place Photos, and Autocomplete.

Documentation: https://developers.google.com/maps/documentation/places/web-service
"""

import requests
from typing import Optional, Dict, List, Any, Union
from dataclasses import dataclass
from enum import Enum


class PlaceField(Enum):
    """Place data fields that can be requested."""
    ID = "id"
    DISPLAY_NAME = "displayName"
    FORMATTED_ADDRESS = "formattedAddress"
    LOCATION = "location"
    PLUS_CODE = "plusCode"
    TYPES = "types"
    PRIMARY_TYPE = "primaryType"
    NATIONAL_PHONE_NUMBER = "nationalPhoneNumber"
    INTERNATIONAL_PHONE_NUMBER = "internationalPhoneNumber"
    WEBSITE_URI = "websiteUri"
    REGULAR_OPENING_HOURS = "regularOpeningHours"
    UTC_OFFSET = "utcOffset"
    VIEWPORT = "viewport"
    ADR_FORMATTED_ADDRESS = "adrFormatAddress"
    BUSINESS_STATUS = "businessStatus"
    ICON = "icon"
    ICON_MASK_BASE_URI = "iconMaskBaseUri"
    ICON_BACKGROUND_COLOR = "iconBackgroundColor"
    SHORT_FORMATTED_ADDRESS = "shortFormattedAddress"
    ADDRESS_COMPONENTS = "addressComponents"
    CURRENT_OPENING_HOURS = "currentOpeningHours"
    PRICE_LEVEL = "priceLevel"
    ATTRIBUTIONS = "attributions"
    USER_RATING_COUNT = "userRatingCount"
    RATING = "rating"
    REVIEWS = "reviews"
    PHOTOS = "photos"
    EDITORIAL_SUMMARY = "editorialSummary"
    WHEELCHAIR_ACCESSIBLE_ENTRANCE = "wheelchairAccessibleEntrance"
    RESERVABLE = "reservable"
    SERVES_BREAKFAST = "servesBreakfast"
    SERVES_LUNCH = "servesLunch"
    SERVES_DINNER = "servesDinner"
    SERVES_BEER = "servesBeer"
    SERVES_BRUNCH = "servesBrunch"
    SERVES_WINE = "servesWine"
    SERVES_VEGETARIAN_FOOD = "servesVegetarianFood"
    TAKEOUT = "takeout"
    DELIVERY = "delivery"
    DINE_IN = "dineIn"
    CURBSIDE_PICKUP = "curbsidePickup"
    OUTDOOR_SEATING = "outdoorSeating"
    LIVE_MUSIC = "liveMusic"
    MENU_FOR_CHILDREN = "menuForChildren"
    SERVES_COCKTAILS = "servesCocktails"
    SERVES_DESSERT = "servesDessert"
    SERVES_COFFEE = "servesCoffee"
    GOOD_FOR_CHILDREN = "goodForChildren"
    ALLOWS_DOGS = "allowsDogs"
    RESTROOM = "restroom"
    GOOD_FOR_GROUPS = "goodForGroups"
    GOOD_FOR_WATCHING_SPORTS = "goodForWatchingSports"
    PAYMENT_OPTIONS = "paymentOptions"
    PARKING_OPTIONS = "parkingOptions"
    SUB_ESTABLISHMENT = "subEstablishment"
    PRIMARY_TYPE_DISPLAY_NAME = "primaryTypeDisplayName"
    SECONDARY_TYPES = "secondaryTypes"
    SECONDARY_TYPE_DISPLAY_NAMES = "secondaryTypeDisplayNames"


@dataclass
class Location:
    """Represents a geographic location."""
    latitude: float
    longitude: float

    def to_dict(self) -> Dict[str, float]:
        """Convert to API format."""
        return {
            "latitude": self.latitude,
            "longitude": self.longitude
        }
    
    @classmethod
    def from_dict(cls, data: Dict[str, float]) -> "Location":
        """Create Location from API response dictionary."""
        return cls(
            latitude=data["latitude"],
            longitude=data["longitude"]
        )


@dataclass
class Place:
    """Represents a place from the Google Places API."""
    id: str
    types: Optional[List[str]] = None
    formatted_address: Optional[str] = None
    location: Optional[Location] = None
    rating: Optional[float] = None
    user_rating_count: Optional[int] = None
    display_name: Optional[str] = None
    display_name_language_code: Optional[str] = None
    primary_type: Optional[str] = None
    
    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> "Place":
        """Create Place from API response dictionary."""
        # Extract display name
        display_name = None
        display_name_language_code = None
        if "displayName" in data and isinstance(data["displayName"], dict):
            display_name = data["displayName"].get("text")
            display_name_language_code = data["displayName"].get("languageCode")
        
        # Extract location
        location = None
        if "location" in data and isinstance(data["location"], dict):
            location = Location.from_dict(data["location"])
        
        return cls(
            id=data.get("id", ""),
            types=data.get("types"),
            formatted_address=data.get("formattedAddress"),
            location=location,
            rating=data.get("rating"),
            user_rating_count=data.get("userRatingCount"),
            display_name=display_name,
            display_name_language_code=display_name_language_code,
            primary_type=data.get("primaryType")
        )


class PlacesAPI:
    """
    Google Places API (New) Client
    
    This class provides methods to interact with the Google Places API (New).
    All methods require a valid API key.

    To find the type of places, you can use the following URL:
    https://developers.google.com/maps/documentation/places/web-service/place-types?hl=es-419
    
    Example:
        >>> api = PlacesAPI(api_key="YOUR_API_KEY")
        >>> results = api.text_search("restaurants in New York")
        >>> details = api.place_details(place_id="ChIJN1t_tDeuEmsRUsoyG83frY4")
    """
    
    BASE_URL = "https://places.googleapis.com/v1"
    
    def __init__(self, api_key: str, debug: bool = False, timeout: Optional[float] = 30.0):
        """
        Initialize the Places API client.
        
        Args:
            api_key: Your Google Maps API key
            debug: If True, print request details for debugging
            timeout: Request timeout in seconds (default: 30.0)
        """
        self.api_key = api_key
        self.debug = debug
        self.timeout = timeout
        self.session = requests.Session()
        self.session.headers.update({
            "Content-Type": "application/json",
            "X-Goog-Api-Key": api_key
        })
    
    def nearby_search(
        self,
        location: Union[Location, Dict[str, float]],
        radius_meters: Optional[int] = None,
        included_types: Optional[List[str]] = None,
        excluded_types: Optional[List[str]] = None,
        included_primary_types: Optional[List[str]] = None,
        excluded_primary_types: Optional[List[str]] = None,
        max_result_count: Optional[int] = None,
        language_code: Optional[str] = None,
        region_code: Optional[str] = None,
        rank_preference: Optional[str] = None,
        location_bias: Optional[Dict[str, Any]] = None,
        location_restriction: Optional[Dict[str, Any]] = None,
        field_mask: Optional[Union[str, List[str]]] = None
    ) -> List[Place]:
        """
        Search for places within a specified area.
        
        Args:
            location: The location to search around (Location object or dict with lat/lng)
            radius_meters: Maximum distance in meters from location to search
            included_types: List of place types to include
            excluded_types: List of place types to exclude
            included_primary_types: List of primary place types to include
            excluded_primary_types: List of primary place types to exclude
            max_result_count: Maximum number of results to return (default: 20)
            language_code: Language code for results (e.g., "en", "es")
            region_code: Region code for results (e.g., "US", "GB")
            rank_preference: How to rank results ("POPULARITY" or "DISTANCE")
            location_bias: Location bias configuration
            location_restriction: Location restriction configuration (overrides default circle)
            field_mask: Fields to return (e.g., "*" for all, or ["places.id", "places.displayName"])
                        Default: common fields
            
        Returns:
            List of Place objects matching the search criteria
            
        Example:
            >>> api = PlacesAPI(api_key="YOUR_API_KEY")
            >>> location = Location(latitude=40.7128, longitude=-74.0060)
            >>> results = api.nearby_search(
            ...     location=location,
            ...     included_primary_types=["restaurant"],
            ...     radius_meters=1000
            ... )
            >>> for place in results:
            ...     print(place.display_name)
        """
        url = f"{self.BASE_URL}/places:searchNearby"
        
        # Convert Location object to dict if needed
        if isinstance(location, Location):
            location = location.to_dict()
        
        payload = {}
        
        # Only include type filters if they are provided (don't send empty arrays)
        if included_types:
            payload["includedTypes"] = included_types
        
        if excluded_types:
            payload["excludedTypes"] = excluded_types
        
        if included_primary_types:
            payload["includedPrimaryTypes"] = included_primary_types
        
        if excluded_primary_types:
            payload["excludedPrimaryTypes"] = excluded_primary_types
        
        # Location restriction is required - use provided one or create default circle
        if location_restriction:
            payload["locationRestriction"] = location_restriction
        else:
            payload["locationRestriction"] = {
                "circle": {
                    "center": location,
                    "radius": radius_meters or 500
                }
            }
        
        if max_result_count is not None:
            payload["maxResultCount"] = max_result_count
        
        if language_code:
            payload["languageCode"] = language_code
        
        if region_code:
            payload["regionCode"] = region_code
        
        if rank_preference:
            payload["rankPreference"] = rank_preference
        
        if location_bias:
            payload["locationBias"] = location_bias
        
        # Prepare field mask header
        headers = self.session.headers.copy()
        if field_mask:
            if isinstance(field_mask, list):
                field_mask_str = ",".join(field_mask)
            else:
                field_mask_str = field_mask
        else:
            # Default field mask with common fields
            field_mask_str = "places.id,places.displayName,places.formattedAddress,places.location,places.rating,places.userRatingCount,places.types,places.primaryType"
        
        headers["X-Goog-FieldMask"] = field_mask_str
        
        if self.debug:
            print(f"Request URL: {url}")
            print(f"Request Headers: {headers}")
            print(f"Request Payload: {payload}")
            print(f"Field Mask: {field_mask_str}")
        
        response = self.session.post(url, json=payload, headers=headers, timeout=self.timeout)
        
        # Provide better error messages for debugging
        if not response.ok:
            try:
                error_detail = response.json()
                error_msg = f"API Error {response.status_code}: {error_detail}"
            except:
                error_msg = f"API Error {response.status_code}: {response.text}"
            if self.debug:
                print(f"Error Response: {error_msg}")
            raise requests.exceptions.HTTPError(error_msg, response=response)
        
        response_data = response.json()
        places_data = response_data.get("places", [])
        return [Place.from_dict(place_data) for place_data in places_data]
    
    def text_search(
        self,
        text_query: str,
        location_bias: Optional[Dict[str, Any]] = None,
        location_restriction: Optional[Dict[str, Any]] = None,
        included_type: Optional[str] = None,
        included_primary_types: Optional[List[str]] = None,
        excluded_primary_types: Optional[List[str]] = None,
        max_result_count: Optional[int] = None,
        language_code: Optional[str] = None,
        region_code: Optional[str] = None,
        rank_preference: Optional[str] = None,
        price_levels: Optional[List[str]] = None,
        strict_type_filtering: Optional[bool] = None,
        field_mask: Optional[Union[str, List[str]]] = None
    ) -> Dict[str, Any]:
        """
        Search for places based on a text query.
        
        Args:
            text_query: Text search string (e.g., "restaurants in New York")
            location_bias: Location bias configuration
            location_restriction: Location restriction configuration
            included_type: Single place type to include
            included_primary_types: List of primary place types to include
            excluded_primary_types: List of primary place types to exclude
            max_result_count: Maximum number of results to return (default: 20)
            language_code: Language code for results (e.g., "en", "es")
            region_code: Region code for results (e.g., "US", "GB")
            rank_preference: How to rank results ("POPULARITY" or "DISTANCE")
            price_levels: List of price levels to filter by ("PRICE_LEVEL_FREE", "PRICE_LEVEL_INEXPENSIVE", etc.)
            strict_type_filtering: Whether to use strict type filtering
            field_mask: Fields to return (e.g., "*" for all, or ["places.id", "places.displayName"])
                        Default: common fields
            
        Returns:
            API response containing places matching the text query
            
        Example:
            >>> api = PlacesAPI(api_key="YOUR_API_KEY")
            >>> results = api.text_search("coffee shops near Times Square")
        """
        url = f"{self.BASE_URL}/places:searchText"
        
        payload = {
            "textQuery": text_query
        }
        
        if location_bias:
            payload["locationBias"] = location_bias
        
        if location_restriction:
            payload["locationRestriction"] = location_restriction
        
        if included_type:
            payload["includedType"] = included_type
        
        if included_primary_types:
            payload["includedPrimaryTypes"] = included_primary_types
        
        if excluded_primary_types:
            payload["excludedPrimaryTypes"] = excluded_primary_types
        
        if max_result_count is not None:
            payload["maxResultCount"] = max_result_count
        
        if language_code:
            payload["languageCode"] = language_code
        
        if region_code:
            payload["regionCode"] = region_code
        
        if rank_preference:
            payload["rankPreference"] = rank_preference
        
        if price_levels:
            payload["priceLevels"] = price_levels
        
        if strict_type_filtering is not None:
            payload["strictTypeFiltering"] = strict_type_filtering
        
        # Prepare field mask header
        headers = self.session.headers.copy()
        if field_mask:
            if isinstance(field_mask, list):
                field_mask_str = ",".join(field_mask)
            else:
                field_mask_str = field_mask
        else:
            # Default field mask with common fields
            field_mask_str = "places.id,places.displayName,places.formattedAddress,places.location,places.rating,places.userRatingCount,places.types,places.primaryType"
        
        headers["X-Goog-FieldMask"] = field_mask_str
        
        if self.debug:
            print(f"Request URL: {url}")
            print(f"Request Headers: {headers}")
            print(f"Request Payload: {payload}")
            print(f"Field Mask: {field_mask_str}")
        
        response = self.session.post(url, json=payload, headers=headers, timeout=self.timeout)
        
        # Provide better error messages for debugging
        if not response.ok:
            try:
                error_detail = response.json()
                error_msg = f"API Error {response.status_code}: {error_detail}"
            except:
                error_msg = f"API Error {response.status_code}: {response.text}"
            if self.debug:
                print(f"Error Response: {error_msg}")
            raise requests.exceptions.HTTPError(error_msg, response=response)
        
        return response.json()
    
    def place_details(
        self,
        place_id: Union[str, Place],
        language_code: Optional[str] = None,
        region_code: Optional[str] = None,
        session_token: Optional[str] = None,
        fields: Optional[List[Union[str, PlaceField]]] = None,
        field_mask: Optional[Union[str, List[str]]] = None
    ) -> Dict[str, Any]:
        """
        Get detailed information about a specific place.
        
        Args:
            place_id: The place ID (can be just the ID or "places/{place_id}"), or a Place object
            language_code: Language code for results (e.g., "en", "es")
            region_code: Region code for results (e.g., "US", "GB")
            session_token: Session token for billing optimization
            fields: List of fields to return (can be strings or PlaceField enums) - DEPRECATED, use field_mask instead
            field_mask: Fields to return (e.g., "*" for all, or ["displayName", "formattedAddress"])
                        If not provided and fields is None, uses "*" to get all fields
            
        Returns:
            API response containing detailed place information
            
        Example:
            >>> api = PlacesAPI(api_key="YOUR_API_KEY")
            >>> details = api.place_details("ChIJN1t_tDeuEmsRUsoyG83frY4")
            >>> # Or use a Place object
            >>> places = api.nearby_search(location=location)
            >>> details = api.place_details(places[0])
        """
        # Extract place_id from Place object if needed
        if isinstance(place_id, Place):
            place_id = place_id.id
        
        # Ensure place_id is in the correct format
        if not place_id.startswith("places/"):
            place_id = f"places/{place_id}"
        
        url = f"{self.BASE_URL}/{place_id}"
        
        params = {}
        if language_code:
            params["languageCode"] = language_code
        if region_code:
            params["regionCode"] = region_code
        if session_token:
            params["sessionToken"] = session_token
        
        # Prepare field mask header
        headers = self.session.headers.copy()
        
        # Handle field_mask (new way) or fields (old way for backward compatibility)
        if field_mask:
            if isinstance(field_mask, list):
                field_mask_str = ",".join(field_mask)
            else:
                field_mask_str = field_mask
        elif fields:
            # Convert PlaceField enums to strings and add "places." prefix if needed
            field_list = [
                field.value if isinstance(field, PlaceField) else field
                for field in fields
            ]
            # Add "places." prefix if not already present
            field_list = [
                f"places.{f}" if not f.startswith("places.") else f
                for f in field_list
            ]
            field_mask_str = ",".join(field_list)
        else:
            # Default: get all fields
            field_mask_str = "*"
        
        headers["X-Goog-FieldMask"] = field_mask_str
        
        if self.debug:
            print(f"Request URL: {url}")
            print(f"Request Headers: {headers}")
            print(f"Request Params: {params}")
            print(f"Field Mask: {field_mask_str}")
        
        response = self.session.get(url, params=params, headers=headers, timeout=self.timeout)
        
        # Provide better error messages for debugging
        if not response.ok:
            try:
                error_detail = response.json()
                error_msg = f"API Error {response.status_code}: {error_detail}"
            except:
                error_msg = f"API Error {response.status_code}: {response.text}"
            if self.debug:
                print(f"Error Response: {error_msg}")
            raise requests.exceptions.HTTPError(error_msg, response=response)
        
        return response.json()
    
    def place_photo(
        self,
        photo_name: str,
        max_width_px: Optional[int] = None,
        max_height_px: Optional[int] = None,
        skip_http_redirect: Optional[bool] = None
    ) -> requests.Response:
        """
        Get a photo for a place.
        
        Args:
            photo_name: The photo name (from place details response, e.g., 
                       "places/ChIJN1t_tDeuEmsRUsoyG83frY4/photos/abc123")
            max_width_px: Maximum width in pixels (required if max_height_px not provided)
            max_height_px: Maximum height in pixels (required if max_width_px not provided)
            skip_http_redirect: Whether to skip HTTP redirect
            
        Returns:
            Response object containing the photo data
            
        Raises:
            ValueError: If neither max_width_px nor max_height_px is provided
            
        Example:
            >>> api = PlacesAPI(api_key="YOUR_API_KEY")
            >>> photo_response = api.place_photo(
            ...     photo_name="places/ChIJN1t_tDeuEmsRUsoyG83frY4/photos/abc123",
            ...     max_width_px=800
            ... )
            >>> with open("photo.jpg", "wb") as f:
            ...     f.write(photo_response.content)
        """
        # Validate that at least one dimension is provided
        if max_width_px is None and max_height_px is None:
            raise ValueError(
                "At least one of 'max_width_px' or 'max_height_px' must be provided. "
                "The Places API requires at least one dimension parameter."
            )
        
        # Ensure photo_name doesn't start with / and doesn't include /media
        photo_name = photo_name.strip("/")
        if photo_name.endswith("/media"):
            photo_name = photo_name[:-6]  # Remove "/media" suffix if present
        
        url = f"{self.BASE_URL}/{photo_name}/media"
        
        params = {}
        if max_width_px is not None:
            params["maxWidthPx"] = max_width_px
        if max_height_px is not None:
            params["maxHeightPx"] = max_height_px
        if skip_http_redirect is not None:
            params["skipHttpRedirect"] = skip_http_redirect
        
        headers = self.session.headers.copy()
        # Remove Content-Type header for GET requests (not needed for media)
        headers.pop("Content-Type", None)
        
        if self.debug:
            print(f"Request URL: {url}")
            print(f"Request Headers: {headers}")
            print(f"Request Params: {params}")
        
        response = self.session.get(url, params=params, headers=headers, timeout=self.timeout)
        
        # Provide better error messages for debugging
        if not response.ok:
            try:
                error_detail = response.json()
                error_msg = f"API Error {response.status_code}: {error_detail}"
            except:
                error_msg = f"API Error {response.status_code}: {response.text}"
            if self.debug:
                print(f"Error Response: {error_msg}")
            raise requests.exceptions.HTTPError(error_msg, response=response)
        
        return response
    
    def autocomplete(
        self,
        input: str,
        location_bias: Optional[Dict[str, Any]] = None,
        location_restriction: Optional[Dict[str, Any]] = None,
        included_primary_types: Optional[List[str]] = None,
        included_region_codes: Optional[List[str]] = None,
        included_primary_type: Optional[str] = None,
        language_code: Optional[str] = None,
        origin: Optional[Union[Location, Dict[str, float]]] = None,
        region_code: Optional[str] = None,
        session_token: Optional[str] = None,
        input_offset: Optional[int] = None,
        field_mask: Optional[Union[str, List[str]]] = None
    ) -> Dict[str, Any]:
        """
        Get place predictions and query predictions based on input text.
        
        Args:
            input: The text input for autocomplete
            location_bias: Location bias configuration
            location_restriction: Location restriction configuration
            included_primary_types: List of primary place types to include
            included_region_codes: List of region codes to include
            included_primary_type: Single primary place type to include
            language_code: Language code for results (e.g., "en", "es")
            origin: Origin location for distance calculations
            region_code: Region code for results (e.g., "US", "GB")
            session_token: Session token for billing optimization
            input_offset: Character offset in the input string
            field_mask: Fields to return (e.g., "*" for all, or ["suggestions.placePrediction.placeId"])
                        Default: common fields for autocomplete
            
        Returns:
            API response containing place predictions
            
        Example:
            >>> api = PlacesAPI(api_key="YOUR_API_KEY")
            >>> predictions = api.autocomplete("New York rest")
        """
        url = f"{self.BASE_URL}/places:autocomplete"
        
        # Convert Location object to dict if needed
        if isinstance(origin, Location):
            origin = origin.to_dict()
        
        payload = {
            "input": input
        }
        
        if location_bias:
            payload["locationBias"] = location_bias
        
        if location_restriction:
            payload["locationRestriction"] = location_restriction
        
        if included_primary_types:
            payload["includedPrimaryTypes"] = included_primary_types
        
        if included_region_codes:
            payload["includedRegionCodes"] = included_region_codes
        
        if included_primary_type:
            payload["includedPrimaryType"] = included_primary_type
        
        if language_code:
            payload["languageCode"] = language_code
        
        if origin:
            payload["origin"] = origin
        
        if region_code:
            payload["regionCode"] = region_code
        
        if session_token:
            payload["sessionToken"] = session_token
        
        if input_offset is not None:
            payload["inputOffset"] = input_offset
        
        response = self.session.post(url, json=payload, timeout=self.timeout)
        
        # Provide better error messages for debugging
        if not response.ok:
            try:
                error_detail = response.json()
                error_msg = f"API Error {response.status_code}: {error_detail}"
            except:
                error_msg = f"API Error {response.status_code}: {response.text}"
            raise requests.exceptions.HTTPError(error_msg, response=response)
        
        return response.json()
    
    def close(self):
        """Close the session."""
        self.session.close()
    
    def __enter__(self):
        """Context manager entry."""
        return self
    
    def __exit__(self, exc_type, exc_val, exc_tb):
        """Context manager exit."""
        self.close()

