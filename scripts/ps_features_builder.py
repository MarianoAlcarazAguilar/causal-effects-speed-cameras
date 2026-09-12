"""
Clase para construir features de propensity score y variables de resultado.

Esta clase encapsula la funcionalidad del notebook ps-features-crafting.ipynb,
permitiendo construir todas las features necesarias para el análisis de propensity
score matching y las variables de resultado, guardando los resultados como
atributos del objeto en lugar de escribirlos a archivos.
"""

from typing import Literal
import warnings
import pandas as pd
import geopandas as gpd
from grid_builder import GridBuilder

warnings.filterwarnings("ignore")


class PSFeaturesBuilder:
    """
    Constructor de features para propensity score y variables de resultado.
    
    Esta clase encapsula la funcionalidad del notebook ps-features-crafting.ipynb,
    permitiendo construir todas las features necesarias para el análisis de propensity
    score matching y las variables de resultado, guardando los resultados como
    atributos del objeto en lugar de escribirlos a archivos.
    
    Soporta dos tipos de cuadrícula:
    - 'rectangular': Cuadrícula tradicional de n × n celdas sobre las vialidades
    - 'circular': Círculos hexagonales alrededor de las cámaras de velocidad
    
    Parameters
    ----------
    paths : dict
        Diccionario con las rutas de los archivos necesarios:
        - 'vialidades': ruta al archivo JSON de vialidades
        - 'speed_cameras': ruta al archivo shapefile de cámaras de velocidad
        - 'metro_coordinates': ruta al archivo parquet de coordenadas del metro
        - 'afluencia_metro': ruta al archivo parquet de afluencia del metro
        - 'classified_incidents': ruta al archivo parquet de incidentes clasificados
        - 'volumen_mensual': ruta al archivo parquet de volumen mensual
    grid_type : {'rectangular', 'circular'}, default='rectangular'
        Tipo de cuadrícula a construir.
    grid_size : int, default=123
        Tamaño de la cuadrícula rectangular (número de celdas por lado).
        Solo se usa cuando grid_type='rectangular'.
    offset_x_m : float, default=0.0
        Desplazamiento en metros en la dirección X al crear la cuadrícula rectangular.
    offset_y_m : float, default=0.0
        Desplazamiento en metros en la dirección Y al crear la cuadrícula rectangular.
    circle_radius : float, default=100.0
        Radio de los círculos en metros. Solo se usa cuando grid_type='circular'.
        Las cámaras que estén a menos de un diámetro (2 × radio) se fusionan
        automáticamente antes de crear los círculos.
    n_circles : int, default=2
        Número de círculos a crear en cada dirección desde el centro.
        Solo se usa cuando grid_type='circular'.
    inicio_operaciones : str, default='2019-04-22'
        Fecha de inicio de las operaciones.
        Este valor realmente no cambia, pero lo estoy dejando como un parámetro para
        poder hacer las pruebas placebo que quiero hacer para mostrar las tendencias 
        paralelas. Esto era más fácil que meterme a hacer manualmente la transformación
    years_before : int, default=3
        Años antes de la fecha de inicio de las operaciones para calcular el from_date.
        Al igual que inicio_operaciones, este valor no debería de cambiar, pero lo agrego
        para poder hacer las pruebas placebo.
    years_after : int, default=3
        Años después de la fecha de inicio de las operaciones para calcular el to_date.
        Al igual que inicio_operaciones, este valor no debería de cambiar, pero lo agrego
        para poder hacer las pruebas placebo.
    
    Attributes
    ----------
    grid : geopandas.GeoDataFrame
        Cuadrícula espacial con las unidades de análisis
    grid_length : float
        Longitud de cada celda en metros (para rectangular) o radio (para circular)
    ps_features : pandas.DataFrame
        Features para el cálculo del propensity score
    outcome : pandas.DataFrame
        Variables de resultado mensuales (accidentes totales, min, pic, fcs)
    merged_cameras : geopandas.GeoDataFrame
        Cámaras fusionadas (solo disponible cuando grid_type='circular')
    
    Examples
    --------
    Cuadrícula rectangular:
    
    >>> paths = {...}
    >>> builder = PSFeaturesBuilder(paths, grid_type='rectangular', grid_size=123)
    >>> builder.build()
    
    Cuadrícula circular:
    
    >>> builder = PSFeaturesBuilder(
    ...     paths,
    ...     grid_type='circular',
    ...     circle_radius=150,
    ...     n_circles=3
    ... )
    >>> builder.build()
    """
    
    def __init__(
        self,
        paths: dict,
        grid_type: Literal['rectangular', 'circular'] = 'rectangular',
        grid_size: int = 123,
        offset_x_m: float = 0.0,
        offset_y_m: float = 0.0,
        circle_radius: float = 100.0,
        n_circles: int = 2,
        inicio_operaciones: str = '2019-04-22',
        years_before: int = 3,
        years_after: int = 3
    ):
        self.paths = paths
        self.grid_type = grid_type
        
        # Parámetros para grid rectangular
        self.grid_size = grid_size
        self.offset_x_m = offset_x_m
        self.offset_y_m = offset_y_m
        
        # Parámetros para grid circular
        self.circle_radius = circle_radius
        self.n_circles = n_circles
        
        self.inicio_operaciones = pd.to_datetime(inicio_operaciones)
        self.from_date = self.inicio_operaciones - pd.Timedelta(days=365*years_before)
        self.to_date = self.inicio_operaciones + pd.Timedelta(days=365*years_after)
        
        # Atributos para almacenar datos cargados
        self.vialidades = None
        self.speed_cameras = None
        self.coordinates = None
        self.afluencia = None
        self.accidents = None
        self.volumen_mensual = None
        self.volumen_semanal = None
        
        # Atributos para almacenar resultados
        self.grid = None
        self.grid_length = None
        self.ps_features = None
        self.outcome = None
        self.merged_cameras = None  # Solo para grid circular
        self._circular_grid_camera_map = None  # Mapeo grid_id -> has_camera para circular
    
    def _load_spatial_data(self):
        """Carga los datos espaciales (vialidades y cámaras de velocidad)."""
        # Cargar vialidades
        self.vialidades = (
            gpd
            .read_file(self.paths['vialidades'])
            .assign(
                tipo_vialidad=lambda x: x.TIPO_VIA.map({
                    "Vía primaria": "primaria",
                    'Vía de acceso controlado': 'acceso_controlado'
                }),
                carriles=lambda x: pd.to_numeric(x.CARRILES, errors='raise'),
                sentidos=lambda x: x.CIRCULA.map({
                    "Un sentido": 1,
                    "Dos sentidos": 2,
                    "Un sentido con carril de contraflujo": 2
                })
            )
            .rename({
                'NIVEL': 'nivel',
                'NOMENCLAT': 'calle',
                'NOMBRE': 'vialidad',
                'ID_VIA': 'id_via'
            }, axis=1)
            [[
                'id_via', 'vialidad', 'calle', 'tipo_vialidad',
                'carriles', 'sentidos', 'nivel', 'geometry'
            ]]
        )
        
        # Cargar cámaras de velocidad
        self.speed_cameras = gpd.read_file(self.paths['speed_cameras'])
    
    def _load_temporal_data(self):
        """Carga los datos temporales (metro, accidentes, volumen)."""
        # Cargar coordenadas del metro
        coords_df = pd.read_parquet(self.paths['metro_coordinates'])
        self.coordinates = (
            gpd.GeoDataFrame(
                data=coords_df.drop(['latitude', 'longitude'], axis=1),
                geometry=gpd.points_from_xy(coords_df.longitude, coords_df.latitude),
                crs="EPSG:4326"
            )
            .set_geometry('geometry')
        )
        
        # Cargar afluencia del metro
        afluencia_df = pd.read_parquet(self.paths['afluencia_metro'])
        self.afluencia = afluencia_df.merge(self.coordinates, on='estacion')
        
        # Cargar accidentes
        accidents_df = pd.read_parquet(self.paths['classified_incidents'])
        self.accidents = (
            gpd.GeoDataFrame(
                data=accidents_df.drop(['latitude', 'longitude'], axis=1),
                geometry=gpd.points_from_xy(
                    accidents_df.longitude,
                    accidents_df.latitude
                ),
                crs="EPSG:4326"
            )
        )
        
        # Cargar volumen mensual
        self.volumen_mensual = pd.read_parquet(self.paths['volumen_mensual'])
        
        # Construir volumen semanal a partir del mensual
        # NOTA: Se asume flujo diario lineal basado en el volumen mensual total
        self.volumen_mensual["end"] = (
            self.volumen_mensual.timestamp + pd.offsets.MonthEnd(1)
        )
        daily_list = []
        
        for _, row in self.volumen_mensual.iterrows():
            start = row['timestamp']
            end = row['end']
            days = (end - start).days + 1
            
            # Volumen diario lineal
            daily_value = row['volumen_mensual'] / days
            
            # Crear rango diario
            r = pd.date_range(start, end, freq='D')
            
            # DataFrame diario para el mes
            temp = pd.DataFrame({
                'fecha': r,
                'volumen_diario': daily_value
            })
            daily_list.append(temp)
        
        self.volumen_semanal = (
            pd
            .concat(daily_list, ignore_index=True)
            .groupby(pd.Grouper(key='fecha', freq="1W"))
            .agg(volumen_semanal=pd.NamedAgg("volumen_diario", "sum"))
            .reset_index()
        )
    
    def _build_grid(self):
        """Construye la cuadrícula espacial según el tipo especificado."""
        if self.grid_type == 'rectangular':
            self._build_rectangular_grid()
        elif self.grid_type == 'circular':
            self._build_circular_grid()
        else:
            raise ValueError(f"grid_type debe ser 'rectangular' o 'circular', no '{self.grid_type}'")
    
    def _build_rectangular_grid(self):
        """Construye una cuadrícula rectangular."""
        grid_response = GridBuilder.build_rectangular_grid(
            self.vialidades,
            self.grid_size,
            offset_x_m=self.offset_x_m,
            offset_y_m=self.offset_y_m
        )
        self.grid = grid_response.get("grid")
        self.grid_length = grid_response.get("length_m")
    
    def _build_circular_grid(self):
        """
        Construye una cuadrícula circular alrededor de las cámaras de velocidad.
        
        1. Fusiona cámaras cercanas (a menos de un diámetro) usando merge_close_points
        2. Crea círculos hexagonales alrededor de cada cámara fusionada
        3. El círculo central (fila=0, columna=0) es el que contiene la cámara
        4. Los círculos circundantes son controles (solo si intersectan con vialidades)
        """
        # Paso 1: Fusionar cámaras que estén a menos de un diámetro de distancia
        # Esto evita que los círculos centrales se solapen
        diametro = int(2 * self.circle_radius)
        self.merged_cameras = GridBuilder.merge_close_points(
            self.speed_cameras,
            distance_threshold=diametro
        )
        
        # Paso 2: Crear círculos hexagonales alrededor de cada cámara fusionada
        circles = GridBuilder.create_circle_grid(
            self.merged_cameras,
            r=self.circle_radius,
            n=self.n_circles
        )
        
        # Paso 3: Determinar cuáles tienen cámara (círculos centrales)
        circles['has_camera'] = ((circles['fila'] == 0) & (circles['columna'] == 0)).astype(int)
        
        # Paso 4: Filtrar controles - solo mantener los que intersectan con vialidades
        # Los círculos con cámara siempre se mantienen
        circles_with_camera = circles[circles['has_camera'] == 1]
        circles_control = circles[circles['has_camera'] == 0]
        
        # Encontrar círculos control que intersectan con vialidades
        circles_intersecting_roads = (
            gpd.sjoin(
                circles_control,
                self.vialidades,
                how='inner',
                predicate='intersects'
            )
            [['original_idx', 'fila', 'columna', 'has_camera', 'geometry']]
            .drop_duplicates(subset=['original_idx', 'fila', 'columna'])
        )
        
        # Filtrar controles que intersectan con cámaras de velocidad
        # (para evitar que un círculo control contenga accidentalmente otra cámara)
        invalid_controls = gpd.sjoin(
            circles_intersecting_roads,
            self.speed_cameras,
            how='inner',
            predicate='intersects'
        ).index.unique()
        
        circles_intersecting_roads = circles_intersecting_roads.drop(invalid_controls)
        
        # Combinar círculos con cámara y círculos control válidos
        circles_filtered = gpd.GeoDataFrame(
            pd.concat([circles_with_camera, circles_intersecting_roads], ignore_index=True),
            crs=circles.crs
        )
        
        # Paso 5: Asignar grid_id único después del filtrado
        circles_filtered['grid_id'] = range(len(circles_filtered))
        
        # Guardar mapeo de cámara para usar en _assign_camera_features
        self._circular_grid_camera_map = circles_filtered[['grid_id', 'has_camera']].copy()
        
        # Agregar centroide y mantener solo las columnas necesarias
        circles_filtered['centroid'] = circles_filtered.geometry.centroid
        
        self.grid = circles_filtered[['grid_id', 'geometry', 'centroid']].copy()
        self.grid_length = self.circle_radius
    
    def _assign_camera_features(self):
        """Asigna features relacionadas con la presencia de cámaras."""
        if self.grid_type == 'circular':
            # Para grid circular, usar el mapeo guardado durante la construcción
            # El círculo central (fila=0, columna=0) tiene la cámara
            return self._circular_grid_camera_map.copy()
        
        # Para grid rectangular, usar spatial join
        grid_has_camera = (
            gpd
            .sjoin(
                left_df=self.grid,
                right_df=self.speed_cameras,
                how="left",
                predicate="intersects"
            )
            .assign(has_camera=lambda x: ~x.index_right.isna())
            .astype({'has_camera': 'int'})
            [['grid_id', 'has_camera']]
            .groupby('grid_id')
            .agg({'has_camera': 'max'})  # Si tiene al menos una cámara, será 1
            .reset_index()
        )
        
        # Asegurar que todos los grids estén presentes (por si acaso)
        all_grids_df = pd.DataFrame({'grid_id': self.grid['grid_id'].unique()})
        grid_has_camera = (
            all_grids_df
            .merge(grid_has_camera, on='grid_id', how='left')
            .fillna({'has_camera': 0})
        )
        
        return grid_has_camera
    
    def _assign_fixed_features(self):
        """Asigna features fijas de las vialidades."""
        fixed_features = (
            gpd
            .sjoin(
                left_df=self.grid,
                right_df=self.vialidades,
                how="left",
                predicate="intersects"
            )
            .groupby("grid_id")
            .agg(
                n_vialidades=pd.NamedAgg("id_via", "nunique"),
                max_carriles=pd.NamedAgg("carriles", "max"),
                both_directions=pd.NamedAgg(
                    "sentidos",
                    lambda x: int(2 in list(x)) if len(list(x)) > 0 else 0
                ),
                via_primaria=pd.NamedAgg(
                    "tipo_vialidad",
                    lambda x: int("primaria" in set(x)) if len(set(x)) > 0 else 0
                ),
                via_acc_cont=pd.NamedAgg(
                    "tipo_vialidad",
                    lambda x: int("acceso_controlado" in set(x)) if len(set(x)) > 0 else 0
                ),
                max_nivel=pd.NamedAgg("nivel", "max")
            )
            .reset_index()
            .fillna({
                'n_vialidades': 0,
                'max_carriles': 0,
                'both_directions': 0,
                'via_primaria': 0,
                'via_acc_cont': 0,
                'max_nivel': 0
            })
        )
        return fixed_features
    
    def _assign_road_length_feature(self):
        """
        Calcula la longitud total de vialidades en metros dentro de cada celda del grid.
        
        Usa intersection para obtener solo la parte de cada vialidad que está
        dentro de la celda, luego calcula la longitud en metros.
        """
        # Convertir a CRS métrico para calcular longitudes correctamente
        grid_m = self.grid.to_crs(GridBuilder.METRIC_CRS)
        vialidades_m = self.vialidades.to_crs(GridBuilder.METRIC_CRS)
        
        # Calcular la intersección de cada vialidad con cada celda
        # y sumar las longitudes por grid_id
        road_lengths = []
        
        for _, grid_row in grid_m.iterrows():
            grid_id = grid_row['grid_id']
            grid_geom = grid_row['geometry']
            
            # Encontrar vialidades que intersectan con esta celda
            intersecting_mask = vialidades_m.intersects(grid_geom)
            intersecting_roads = vialidades_m[intersecting_mask]
            
            if len(intersecting_roads) == 0:
                road_lengths.append({'grid_id': grid_id, 'road_length_m': 0.0})
                continue
            
            # Calcular la intersección y sumar longitudes
            total_length = 0.0
            for _, road in intersecting_roads.iterrows():
                try:
                    intersection = road['geometry'].intersection(grid_geom)
                    if not intersection.is_empty:
                        total_length += intersection.length
                except Exception:
                    continue
            
            road_lengths.append({'grid_id': grid_id, 'road_length_m': round(total_length, 2)})
        
        return pd.DataFrame(road_lengths)
    
    def _assign_metro_features(self):
        """Asigna features relacionadas con la afluencia del metro."""
        # Primero procesamos los datos de afluencia
        afluencia_processed = (
            self.afluencia
            .query('before_treatment')
            .groupby([
                'estacion',
                'geometry',
                pd.Grouper(key='fecha', freq='1M')
            ])
            .agg(afluencia_mensual=pd.NamedAgg('afluencia_total', 'sum'))
            .reset_index()
            .assign(fecha=lambda x: x.fecha + pd.offsets.MonthEnd(0))
            .merge(self.volumen_mensual, left_on='fecha', right_on='end')
            .assign(
                tasa_afluencia_mensual=lambda x: (
                    x.afluencia_mensual / x.volumen_mensual
                )
            )
            .groupby(["estacion", "geometry"])
            .agg(
                mean_afluencia_mensual=pd.NamedAgg(
                    "tasa_afluencia_mensual", "mean"
                ),
                std_afluencia_mensual=pd.NamedAgg(
                    "tasa_afluencia_mensual", "std"
                ),
            )
            .reset_index()
        )
        
        # Hacer el spatial join con left para incluir todos los grids
        affluence_temp = (
            gpd
            .sjoin_nearest(
                left_df=self.grid.set_geometry('centroid').to_crs(epsg=6933),
                right_df=afluencia_processed.set_geometry('geometry').to_crs(epsg=6933),
                how='left',
                distance_col='distance_to_station'
            )
            .drop_duplicates(subset='grid_id', keep='first')
            [[
                "grid_id",
                "mean_afluencia_mensual",
                "std_afluencia_mensual",
                "distance_to_station"
            ]]
        )
        
        # Calcular distancia máxima para usar como valor por defecto
        max_distance = affluence_temp['distance_to_station'].max()
        if pd.isna(max_distance):
            max_distance = 100000  # Valor por defecto si no hay ninguna distancia
        
        affluence = affluence_temp.fillna({
            'mean_afluencia_mensual': 0,
            'std_afluencia_mensual': 0,
            'distance_to_station': max_distance * 2  # Usar el doble de la distancia máxima como valor por defecto
        })
        return affluence
    
    def _assign_accident_features(self):
        """Asigna features relacionadas con tendencias de accidentes."""
        # Primero obtener los accidentes que intersectan con los grids
        accidents_monthly = (
            gpd
            .sjoin(
                left_df=self.grid,
                right_df=self.accidents.query('before_treatment'),
                how='inner',  # Solo grids con accidentes primero
                predicate='intersects'
            )
            .assign(
                min=lambda x: (x.incident_level == 'MIN').astype(int),
                pic=lambda x: (x.incident_level == 'PIC').astype(int),
                fcs=lambda x: (x.incident_level == 'FCS').astype(int)
            )
            .groupby([
                pd.Grouper(key='grid_id'),
                pd.Grouper(key='incident_level'),
                pd.Grouper(key='timestamp', freq='1M')
            ])
            .agg(
                total=pd.NamedAgg('folio', 'count'),
                min=pd.NamedAgg('min', 'sum'),
                pic=pd.NamedAgg('pic', 'sum'),
                fcs=pd.NamedAgg('fcs', 'sum')
            )
            .reset_index()
        )
        
        # Crear índice completo con todos los grids
        full_months = pd.period_range('2016-04-01', '2022-04-01', freq='M')
        unique_grids = self.grid['grid_id'].unique()  # Todos los grids
        unique_levels = ['MIN', 'PIC', 'FCS']  # Niveles conocidos
        
        full_index = pd.MultiIndex.from_product(
            [unique_grids, unique_levels, full_months],
            names=['grid_id', 'incident_level', 'timestamp']
        )
        
        monthly_accidents_tendencies = (
            accidents_monthly
            .assign(timestamp=lambda x: x.timestamp.dt.to_period("M"))
            .set_index(['grid_id', 'incident_level', 'timestamp'])
            .reindex(full_index, fill_value=0)  # Llenar con 0 los grids sin accidentes
            .reset_index()
            .assign(timestamp=lambda x: x.timestamp.dt.to_timestamp())
            .drop(columns=['timestamp', 'incident_level'])
            .groupby(['grid_id'])
            .agg(["mean", "std"])
        )
        
        monthly_accidents_tendencies.columns = [
            f"{stat}_{metric}"
            for metric, stat in monthly_accidents_tendencies.columns
        ]
        monthly_accidents_tendencies.reset_index(inplace=True)
        
        # Asegurar que todos los grids estén presentes (incluso los que nunca tuvieron accidentes)
        all_grids_df = pd.DataFrame({'grid_id': unique_grids})
        monthly_accidents_tendencies = (
            all_grids_df
            .merge(monthly_accidents_tendencies, on='grid_id', how='left')
            .fillna(0)  # Llenar con 0 los grids que nunca tuvieron accidentes
        )
        
        return monthly_accidents_tendencies
    
    def _build_ps_features(self):
        """Construye el dataframe final de features para propensity score."""
        grid_has_camera = self._assign_camera_features()
        fixed_features = self._assign_fixed_features()
        road_length = self._assign_road_length_feature()
        affluence = self._assign_metro_features()
        monthly_accidents_tendencies = self._assign_accident_features()
        
        # Asegurar que todos los merges sean left para mantener todos los grids
        # Partir del grid_has_camera que debería tener todos los grids
        self.ps_features = (
            grid_has_camera
            .merge(fixed_features, on='grid_id', how='left')
            .merge(road_length, on='grid_id', how='left')
            .merge(affluence, on='grid_id', how='left')
            .merge(monthly_accidents_tendencies, on='grid_id', how='left')
            .fillna(0)  # Llenar cualquier NaN restante con 0
        )
    
    def _build_outcome_variables(self):
        """Construye las variables de resultado (outcome) mensuales."""
        all_accidents_monthly = (
            gpd
            .sjoin(
                left_df=self.grid,
                right_df=self.accidents,
                how='inner',
                predicate='intersects'
            )
            .assign(
                min=lambda x: (x.incident_level == 'MIN').astype(int),
                pic=lambda x: (x.incident_level == 'PIC').astype(int),
                fcs=lambda x: (x.incident_level == 'FCS').astype(int)
            )
            .groupby([
                pd.Grouper(key='grid_id'),
                pd.Grouper(key='incident_level'),
                pd.Grouper(key='timestamp', freq='1M')
            ])
            .agg(
                total=pd.NamedAgg('folio', 'count'),
                min=pd.NamedAgg('min', 'sum'),
                pic=pd.NamedAgg('pic', 'sum'),
                fcs=pd.NamedAgg('fcs', 'sum')
            )
            .reset_index()
        )
        
        full_months = pd.period_range('2016-04-01', '2022-04-01', freq='M')
        unique_grids = all_accidents_monthly['grid_id'].unique()
        unique_levels = all_accidents_monthly['incident_level'].unique()
        
        full_index = pd.MultiIndex.from_product(
            [unique_grids, unique_levels, full_months],
            names=['grid_id', 'incident_level', 'timestamp']
        )
        
        # Asegurar que volumen_mensual no tenga duplicados por timestamp
        volumen_mensual_clean = (
            self.volumen_mensual[['timestamp', 'volumen_mensual']]
            .drop_duplicates(subset=['timestamp'], keep='first')
        )
        
        self.outcome = (
            all_accidents_monthly
            .assign(timestamp=lambda x: x.timestamp.dt.to_period("M"))
            .set_index(['grid_id', 'incident_level', 'timestamp'])
            .reindex(full_index)
            .fillna(0)
            .reset_index()
            .assign(timestamp=lambda x: x.timestamp.dt.to_timestamp())
            .merge(
                volumen_mensual_clean,
                on='timestamp',
                how='left'
            )
            .drop(columns=['incident_level'])
            .groupby(['grid_id', 'timestamp'], as_index=False)
            .agg({
                'total': 'sum',
                'min': 'sum',
                'pic': 'sum',
                'fcs': 'sum',
                'volumen_mensual': 'first'
            })
            .sort_values(["grid_id", "timestamp"], ignore_index=True)
        )
    
    def build(self):
        """
        Ejecuta todo el proceso de construcción de features y variables de resultado.
        
        Este método carga todos los datos, construye la cuadrícula, asigna todas
        las features y genera las variables de resultado. Los resultados se
        almacenan en los atributos del objeto:
        - self.grid: GeoDataFrame con la cuadrícula
        - self.grid_length: longitud de cada celda en metros
        - self.ps_features: DataFrame con las features para propensity score
        - self.outcome: DataFrame con las variables de resultado
        """
        # Cargar datos
        self._load_spatial_data()
        self._load_temporal_data()
        
        # Construir cuadrícula
        self._build_grid()
        
        # Construir features de propensity score
        self._build_ps_features()
        
        # Construir variables de resultado
        self._build_outcome_variables()
    
    def save_results(self, output_dir: str):
        """
        Guarda los resultados en archivos.
        
        Parameters
        ----------
        output_dir : str
            Directorio donde se guardarán los archivos
        """
        import os
        
        if self.ps_features is not None:
            self.ps_features.to_parquet(
                os.path.join(output_dir, "grid-propensity-score-features.parquet"),
                index=False
            )
        
        if self.grid is not None:
            self.grid.to_feather(
                os.path.join(output_dir, "grid.parquet"),
                index=False
            )
        
        if self.outcome is not None:
            self.outcome.to_parquet(
                os.path.join(output_dir, "outcome-variables.parquet"),
                index=False
            )

