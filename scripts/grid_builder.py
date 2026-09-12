"""
Módulo para crear geometrías espaciales mediante la clase GridBuilder:
- Cuadrícula rectangular a partir de un GeoDataFrame
- Cuadrícula de círculos en patrón hexagonal a partir de puntos
- Ensanchamiento de LineStrings con segmentación
"""

import math
from typing import Dict, Any

import geopandas as gpd
import numpy as np
from shapely.geometry import Point, LineString, Polygon
from shapely.ops import unary_union, substring
from shapely import get_parts


class GridBuilder:
    """
    Clase para crear diferentes tipos de cuadrículas geométricas.
    
    Todos los métodos trabajan con GeoDataFrames y manejan automáticamente
    la conversión de CRS a metros (EPSG:6372) y de vuelta al CRS original.
    
    Examples
    --------
    >>> from circle_grid import GridBuilder
    >>> 
    >>> # Cuadrícula rectangular
    >>> result = GridBuilder.build_rectangular_grid(streets_gdf, n=10)
    >>> grid = result['grid']
    >>> 
    >>> # Cuadrícula de círculos hexagonal
    >>> circles = GridBuilder.create_circle_grid(points_gdf, r=100, n=2)
    >>> 
    >>> # Ensanchar LineStrings
    >>> segments = GridBuilder.widen_linestrings(lines_gdf, width=50, segment_length=100)
    """
    
    METRIC_CRS = "EPSG:6372"  # CRS métrico para México
    
    # =========================================================================
    # Métodos auxiliares privados
    # =========================================================================
    
    @staticmethod
    def _create_rectangular_cells(
        upper_left: tuple, 
        lower_right: tuple, 
        n: int, 
        crs: str
    ) -> gpd.GeoDataFrame:
        """
        Crea una cuadrícula de n × n celdas rectangulares.
        
        Parameters
        ----------
        upper_left : tuple
            Coordenadas (x, y) de la esquina superior izquierda.
        lower_right : tuple
            Coordenadas (x, y) de la esquina inferior derecha.
        n : int
            Número de celdas en cada dimensión.
        crs : str
            Sistema de coordenadas para el GeoDataFrame resultante.
            
        Returns
        -------
        gpd.GeoDataFrame
            GeoDataFrame con las celdas de la cuadrícula.
        """
        minx, maxy = upper_left
        maxx, miny = lower_right

        cell_width = (maxx - minx) / n
        cell_height = (maxy - miny) / n

        polygons = []
        for i in range(n):
            for j in range(n):
                x1 = minx + i * cell_width
                y1 = maxy - j * cell_height
                x2 = x1 + cell_width
                y2 = y1 - cell_height
                polygons.append(
                    Polygon([(x1, y1), (x2, y1), (x2, y2), (x1, y2)])
                )

        return (
            gpd.GeoDataFrame({'geometry': polygons}, crs=crs)
            .reset_index()
            .rename({'index': 'grid_id'}, axis=1)
            .assign(centroid=lambda x: x.centroid)
        )
    
    # =========================================================================
    # Métodos públicos para crear cuadrículas
    # =========================================================================
    
    @classmethod
    def build_rectangular_grid(
        cls,
        gdf: gpd.GeoDataFrame, 
        n: int, 
        offset_x_m: float = 0, 
        offset_y_m: float = 0
    ) -> Dict[str, Any]:
        """
        Crea una cuadrícula rectangular de n × n celdas.
        
        La cuadrícula se crea basándose en los bounds del GeoDataFrame de entrada,
        opcionalmente desplazada en x e y. Solo se retornan las celdas que
        intersectan con las geometrías del GeoDataFrame original.
        
        Parameters
        ----------
        gdf : gpd.GeoDataFrame
            GeoDataFrame de referencia para definir los límites de la cuadrícula.
        n : int
            Número de celdas en cada dimensión (crea n × n celdas).
        offset_x_m : float, optional
            Desplazamiento horizontal en metros (default: 0).
        offset_y_m : float, optional
            Desplazamiento vertical en metros (default: 0).
            
        Returns
        -------
        Dict[str, Any]
            Diccionario con:
            - 'grid': GeoDataFrame con las celdas de la cuadrícula
            - 'length_m': Longitud del lado de cada celda en metros
        """
        original_crs = gdf.crs
        gdf_m = gdf.to_crs(cls.METRIC_CRS)
        
        # Calcular bounds originales y expandirlos según el offset
        minx_orig, miny_orig, maxx_orig, maxy_orig = gdf_m.total_bounds
        
        minx = minx_orig + min(0, offset_x_m)
        maxx = maxx_orig + max(0, offset_x_m)
        miny = miny_orig + min(0, offset_y_m)
        maxy = maxy_orig + max(0, offset_y_m)
        
        # Crear cuadrícula con bounds expandidos
        upper_left = (minx, maxy)
        lower_right = (maxx, miny)
        grid_m = cls._create_rectangular_cells(upper_left, lower_right, n, cls.METRIC_CRS)
        
        # Desplazar geometrías para el spatial join si hay offset
        if offset_x_m != 0 or offset_y_m != 0:
            gdf_m_offset = gdf_m.copy()
            gdf_m_offset["geometry"] = gdf_m_offset.translate(xoff=offset_x_m, yoff=offset_y_m)
        else:
            gdf_m_offset = gdf_m
        
        # Intersección para quedarse solo con celdas relevantes
        squares_with_data = (
            gpd.sjoin(gdf_m_offset, grid_m, how="left", predicate="intersects")
            [['grid_id']]
            .drop_duplicates()
        )
        
        final_grid_m = grid_m.merge(squares_with_data, on='grid_id')
        
        # Calcular longitud de celda en metros
        area = final_grid_m.area.values[0]
        length = round(math.sqrt(area), 2)
        
        # Regresar al CRS original
        final_grid = final_grid_m.to_crs(original_crs)
        final_grid['centroid'] = final_grid.geometry.centroid
        
        return {
            "grid": final_grid,
            "length_m": length
        }
    
    @classmethod
    def create_circle_grid(
        cls,
        gdf: gpd.GeoDataFrame, 
        r: float, 
        n: int
    ) -> gpd.GeoDataFrame:
        """
        Crea una cuadrícula de círculos en patrón hexagonal alrededor de cada punto.
        
        Para cada punto del GeoDataFrame de entrada, crea:
        - Un círculo central de radio r
        - n círculos a la izquierda y n a la derecha (horizontal)
        - n círculos arriba y n abajo, usando geometría hexagonal (ángulo de 60°)
        
        Parameters
        ----------
        gdf : gpd.GeoDataFrame
            GeoDataFrame con geometría de puntos.
        r : float
            Radio de los círculos en metros.
        n : int
            Número de círculos a crear en cada dirección desde el centro.
            
        Returns
        -------
        gpd.GeoDataFrame
            GeoDataFrame con todos los círculos generados, en el CRS original.
            Columnas: original_idx, fila, columna, geometry
        """
        original_crs = gdf.crs
        gdf_metros = gdf.to_crs(cls.METRIC_CRS)
        
        diametro = 2 * r
        dx_vertical = r  # desplazamiento horizontal para filas arriba/abajo
        dy_vertical = r * np.sqrt(3)  # desplazamiento vertical (60°)
        
        circulos = []
        indices_originales = []
        posiciones = []
        
        for idx, row in gdf_metros.iterrows():
            punto_central = row.geometry
            cx, cy = punto_central.x, punto_central.y
            
            for fila in range(-n, n + 1):
                y_offset = fila * dy_vertical
                
                # Filas impares tienen desplazamiento horizontal
                x_base_offset = dx_vertical if fila % 2 != 0 else 0
                
                for col in range(-n, n + 1):
                    x_offset = x_base_offset + col * diametro
                    nuevo_cx = cx + x_offset
                    nuevo_cy = cy + y_offset
                    
                    circulo = Point(nuevo_cx, nuevo_cy).buffer(r)
                    circulos.append(circulo)
                    indices_originales.append(idx)
                    posiciones.append((fila, col))
        
        gdf_circulos = gpd.GeoDataFrame(
            {
                'original_idx': indices_originales,
                'fila': [p[0] for p in posiciones],
                'columna': [p[1] for p in posiciones],
            },
            geometry=circulos,
            crs=cls.METRIC_CRS
        )
        
        return gdf_circulos.to_crs(original_crs)
    
    @classmethod
    def merge_close_points(
        cls,
        gdf: gpd.GeoDataFrame,
        distance_threshold: int
    ) -> gpd.GeoDataFrame:
        """
        Fusiona puntos que están más cerca que el umbral de distancia.
        
        Si dos puntos están a menos de `distance_threshold` metros, se reemplazan
        ambos por el punto medio entre ellos. El proceso se repite hasta que no
        queden puntos cercanos.
        
        Parameters
        ----------
        gdf : gpd.GeoDataFrame
            GeoDataFrame con geometría de puntos.
        distance_threshold : int
            Distancia umbral en metros. Puntos más cercanos que esto serán fusionados.
            
        Returns
        -------
        gpd.GeoDataFrame
            GeoDataFrame con los puntos finales (fusionados donde corresponda),
            en el CRS original.
        """
        original_crs = gdf.crs
        gdf_m = gdf.to_crs(cls.METRIC_CRS).copy().reset_index(drop=True)
        
        # Obtener solo la columna de geometría para trabajar
        points = list(gdf_m.geometry)
        
        changed = True
        while changed and len(points) > 1:
            changed = False
            n = len(points)
            
            # Crear GeoDataFrame temporal para usar índice espacial
            temp_gdf = gpd.GeoDataFrame(geometry=points, crs=cls.METRIC_CRS)
            
            # Crear buffers para encontrar candidatos cercanos
            buffers = temp_gdf.geometry.buffer(distance_threshold)
            buffered_gdf = gpd.GeoDataFrame(
                {'idx': range(n)},
                geometry=buffers,
                crs=cls.METRIC_CRS
            )
            
            # Usar sjoin para encontrar puntos dentro de los buffers
            temp_gdf['idx'] = range(n)
            joined = gpd.sjoin(
                temp_gdf,
                buffered_gdf,
                how='inner',
                predicate='within'
            )
            
            # Filtrar auto-uniones y obtener pares únicos (idx_left < idx_right)
            pairs = joined[joined['idx_left'] < joined['idx_right']][['idx_left', 'idx_right']].values
            
            if len(pairs) == 0:
                break
            
            # Verificar distancia real y fusionar el primer par válido
            for idx1, idx2 in pairs:
                idx1, idx2 = int(idx1), int(idx2)
                p1, p2 = points[idx1], points[idx2]
                
                if p1.distance(p2) < distance_threshold:
                    # Calcular punto medio
                    midpoint = Point((p1.x + p2.x) / 2, (p1.y + p2.y) / 2)
                    
                    # Crear nueva lista sin los puntos fusionados
                    points = [p for i, p in enumerate(points) if i not in (idx1, idx2)]
                    points.append(midpoint)
                    
                    changed = True
                    break
        
        # Crear GeoDataFrame resultado
        result = gpd.GeoDataFrame(
            {'point_id': range(len(points))},
            geometry=points,
            crs=cls.METRIC_CRS
        )
        
        return result.to_crs(original_crs)
    
    @classmethod
    def widen_linestrings(
        cls,
        gdf: gpd.GeoDataFrame,
        width: float,
        segment_length: float
    ) -> gpd.GeoDataFrame:
        """
        Ensancha LineStrings convirtiéndolos en rectángulos segmentados.
        
        Toma cada LineString, lo ensancha (buffer) y lo segmenta cada 
        `segment_length` metros. Si hay LineStrings cuyos buffers se solapan,
        se fusionan para evitar polígonos duplicados.
        
        Parameters
        ----------
        gdf : gpd.GeoDataFrame
            GeoDataFrame con geometría de LineString o MultiLineString.
        width : float
            Ancho del ensanchamiento en metros (mitad a cada lado de la línea).
        segment_length : float
            Longitud de cada segmento en metros.
            
        Returns
        -------
        gpd.GeoDataFrame
            GeoDataFrame con polígonos rectangulares que siguen la forma
            de las líneas originales, sin solapamientos.
            Columnas: segment_id, geometry
        """
        original_crs = gdf.crs
        gdf_metros = gdf.to_crs(cls.METRIC_CRS)
        
        # Recolectar todas las líneas (expandir MultiLineStrings)
        all_lines = []
        for geom in gdf_metros.geometry:
            if geom is None or geom.is_empty:
                continue
            if geom.geom_type == 'MultiLineString':
                all_lines.extend(list(geom.geoms))
            elif geom.geom_type == 'LineString':
                all_lines.append(geom)
        
        if not all_lines:
            return gpd.GeoDataFrame(geometry=[], crs=original_crs)
        
        # Crear segmentos directamente usando substring (mucho más eficiente)
        all_segment_buffers = []
        for line in all_lines:
            line_length = line.length
            num_segments = max(1, int(np.ceil(line_length / segment_length)))
            
            for i in range(num_segments):
                start_dist = i * segment_length
                end_dist = min((i + 1) * segment_length, line_length)
                
                # Extraer el segmento de línea usando substring
                segment_line = substring(line, start_dist, end_dist)
                
                if segment_line is None or segment_line.is_empty:
                    continue
                
                # Crear buffer del segmento con extremos planos
                segment_buffer = segment_line.buffer(width, cap_style='flat')
                
                if not segment_buffer.is_empty:
                    all_segment_buffers.append(segment_buffer)
        
        if not all_segment_buffers:
            return gpd.GeoDataFrame(geometry=[], crs=original_crs)
        
        # Crear GeoDataFrame con todos los segmentos
        gdf_segments = gpd.GeoDataFrame(
            geometry=all_segment_buffers,
            crs=cls.METRIC_CRS
        )
        
        # Usar overlay con unary_union para fusionar segmentos que se solapan
        # Primero unificamos todos los segmentos
        unified = unary_union(all_segment_buffers)
        
        # Extraer las partes individuales (polígonos no solapados)
        parts = get_parts(unified)
        
        # Filtrar geometrías válidas
        valid_segments = [
            part for part in parts
            if part is not None and not part.is_empty and part.geom_type in ('Polygon', 'MultiPolygon')
        ]
        
        gdf_result = gpd.GeoDataFrame(
            {'segment_id': range(len(valid_segments))},
            geometry=valid_segments,
            crs=cls.METRIC_CRS
        )
        
        return gdf_result.to_crs(original_crs)


# =============================================================================
# Funciones de compatibilidad (wrappers para mantener retrocompatibilidad)
# =============================================================================

def build_grid(
    df: gpd.GeoDataFrame, 
    n: int, 
    offset_x_m: float = 0, 
    offset_y_m: float = 0
) -> Dict[str, Any]:
    """Wrapper de compatibilidad. Usar GridBuilder.build_rectangular_grid()"""
    return GridBuilder.build_rectangular_grid(df, n, offset_x_m, offset_y_m)


def create_circle_grid(
    gdf: gpd.GeoDataFrame, 
    r: float, 
    n: int
) -> gpd.GeoDataFrame:
    """Wrapper de compatibilidad. Usar GridBuilder.create_circle_grid()"""
    return GridBuilder.create_circle_grid(gdf, r, n)


def widen_linestrings(
    gdf: gpd.GeoDataFrame,
    width: float,
    segment_length: float
) -> gpd.GeoDataFrame:
    """Wrapper de compatibilidad. Usar GridBuilder.widen_linestrings()"""
    return GridBuilder.widen_linestrings(gdf, width, segment_length)


def merge_close_points(
    gdf: gpd.GeoDataFrame,
    distance_threshold: int
) -> gpd.GeoDataFrame:
    """Wrapper de compatibilidad. Usar GridBuilder.merge_close_points()"""
    return GridBuilder.merge_close_points(gdf, distance_threshold)


# =============================================================================
# Ejemplo de uso
# =============================================================================

if __name__ == "__main__":
    import matplotlib.pyplot as plt
    
    # ========== Ejemplo 1: Cuadrícula de círculos ==========
    print("=" * 50)
    print("Ejemplo 1: Cuadrícula de círculos")
    print("=" * 50)
    
    punto_ejemplo = gpd.GeoDataFrame(
        {'nombre': ['Centro']},
        geometry=[Point(-99.1332, 19.4326)],
        crs="EPSG:4326"
    )
    
    circulos = GridBuilder.create_circle_grid(punto_ejemplo, r=100, n=2)
    
    print(f"Se crearon {len(circulos)} círculos")
    print(circulos.head(10))
    
    fig, ax = plt.subplots(figsize=(10, 10))
    circulos.plot(ax=ax, alpha=0.3, edgecolor='black')
    punto_ejemplo.plot(ax=ax, color='red', markersize=50)
    plt.title("Cuadrícula de círculos en patrón hexagonal")
    plt.savefig("circle_grid_example.png", dpi=150, bbox_inches='tight')
    plt.show()
    
    # ========== Ejemplo 2: Ensanchamiento de LineStrings ==========
    print("\n" + "=" * 50)
    print("Ejemplo 2: Ensanchamiento de LineStrings")
    print("=" * 50)
    
    lineas_ejemplo = gpd.GeoDataFrame(
        {'nombre': ['Calle 1', 'Calle 2']},
        geometry=[
            LineString([
                (-99.135, 19.430),
                (-99.133, 19.432),
                (-99.130, 19.433),
                (-99.127, 19.432),
            ]),
            LineString([
                (-99.133, 19.428),
                (-99.132, 19.431),
                (-99.131, 19.434),
            ]),
        ],
        crs="EPSG:4326"
    )
    
    segmentos = GridBuilder.widen_linestrings(lineas_ejemplo, width=50, segment_length=100)
    
    print(f"Se crearon {len(segmentos)} segmentos")
    print(segmentos.head(10))
    
    fig, ax = plt.subplots(figsize=(10, 10))
    segmentos.plot(ax=ax, alpha=0.4, edgecolor='black', cmap='tab20')
    lineas_ejemplo.plot(ax=ax, color='red', linewidth=2)
    plt.title("LineStrings ensanchados y segmentados")
    plt.savefig("widen_linestrings_example.png", dpi=150, bbox_inches='tight')
    plt.show()
    
    # ========== Ejemplo 3: Cuadrícula rectangular ==========
    print("\n" + "=" * 50)
    print("Ejemplo 3: Cuadrícula rectangular")
    print("=" * 50)
    
    result = GridBuilder.build_rectangular_grid(lineas_ejemplo, n=5)
    grid = result['grid']
    length_m = result['length_m']
    
    print(f"Se crearon {len(grid)} celdas")
    print(f"Tamaño de celda: {length_m} metros")
    print(grid.head())
    
    fig, ax = plt.subplots(figsize=(10, 10))
    grid.plot(ax=ax, alpha=0.3, edgecolor='black')
    lineas_ejemplo.plot(ax=ax, color='red', linewidth=2)
    plt.title(f"Cuadrícula rectangular ({length_m}m x {length_m}m)")
    plt.savefig("rectangular_grid_example.png", dpi=150, bbox_inches='tight')
    plt.show()
