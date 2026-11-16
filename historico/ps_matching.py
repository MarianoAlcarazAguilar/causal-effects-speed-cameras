"""
Clase para calcular propensity score y realizar matching.

Esta clase encapsula la funcionalidad del notebook ps-matching.ipynb,
permitiendo calcular el propensity score, realizar el matching entre
unidades tratadas y de control, y evaluar la calidad del matching mediante
Standardized Mean Difference (SMD). Los resultados se almacenan como
atributos del objeto en lugar de escribirlos a archivos.
"""

import warnings
from typing import TYPE_CHECKING

import numpy as np
import pandas as pd
import seaborn as sns
import matplotlib.pyplot as plt
from sklearn.linear_model import LogisticRegression

if TYPE_CHECKING:
    import geopandas as gpd

warnings.filterwarnings("ignore")


class PSMatching:
    """
    Calculadora de propensity score y matching.
    
    Esta clase calcula el propensity score para cada unidad de la cuadrícula,
    realiza el matching entre unidades tratadas (con cámara) y de control
    (sin cámara), y evalúa la calidad del matching mediante Standardized
    Mean Difference (SMD) antes y después del matching.
    
    Parameters
    ----------
    ps_features : pandas.DataFrame
        Features para el cálculo del propensity score (de PSFeaturesBuilder.ps_features)
    grid : gpd.GeoDataFrame
        Cuadrícula espacial con las unidades de análisis (de PSFeaturesBuilder.grid)
    outcome : pandas.DataFrame
        Variables de resultado (accidentes) por grid y tiempo (de PSFeaturesBuilder.outcome)
    grid_type : {'rectangular', 'circular'}, default='rectangular'
        Tipo de cuadrícula. Determina qué diccionario de columnas a excluir usar.
    grid_size : int, default=123
        Tamaño de la cuadrícula usado para determinar qué columnas excluir del PS.
        Solo se usa si drop_columns es None y grid_type es 'rectangular'.
    drop_columns : list[str], optional
        Lista de columnas a excluir del cálculo del propensity score.
        Si es None, se usa el diccionario correspondiente según grid_type y grid_size.
    
    Attributes
    ----------
    propensity_score : pandas.DataFrame
        DataFrame con grid_id, propensity_score y has_camera
    matching : dict
        Diccionario con el matching {treated_grid_id: [matched_control_grid_ids]}
    matched_grids : pandas.DataFrame
        Features de los grids que fueron emparejados
    smd_df : pandas.DataFrame
        DataFrame con los valores de SMD antes y después del matching
    outcome_comparison : pandas.DataFrame
        DataFrame con comparación de tasas de accidentes entre tratamiento y control
    """
    
    # Diccionario de columnas a excluir según el tamaño del grid (rectangular)
    DROP_COLUMNS_DICT_RECTANGULAR = {
        123: [  # 300 m
            "mean_min", "std_min",
            "max_carriles",
            "via_primaria",
            "via_acc_cont",
            "both_directions"
        ],
        185: [  # 200 m
            "max_carriles",
            "via_acc_cont",
            "both_directions",
            "n_vialidades"
        ],
        368: [  # 100 m
            "max_carriles",
            "via_primaria",
            "via_acc_cont",
            "both_directions",
            "n_vialidades"
        ],
        500: [  # 75 m
            "mean_min", "std_min",
            "mean_fcs", "std_fcs",
            "max_carriles",
            "via_primaria",
            "via_acc_cont",
            "both_directions",
            "n_vialidades"
        ]
    }
    
    # Diccionario de columnas a excluir para grid circular (por construir)
    DROP_COLUMNS_DICT_CIRCULAR = {
        37.5: [ # optimizado con combinación de 3 variables
            'road_length_m', 
            'distance_to_station', 
            'std_total'
        ],
        50: [ # optimizado con combinación de 3 variables
            'via_primaria', 
            'distance_to_station', 
            'mean_min'
        ],
        100: [ # optimizado con combinación de 3 variables
            'via_primaria', 
            'road_length_m', 
            'distance_to_station'
        ],
        150: [ # optimizado con combinación de 3 variables
            'max_carriles',
            'road_length_m',
            'distance_to_station'
        ],
        200: [ # optimizado con combinación de 3 variables
            'max_carriles',
            'road_length_m',
            'distance_to_station'
        ], 
        250: [ # optimizado con combinación de 3 variables
            'both_directions',
            'road_length_m',
            'distance_to_station'
        ]
    }
    
    # Variables para cálculo de SMD
    VARIABLES_CONTINUAS = [
        "mean_afluencia_mensual",
        "std_afluencia_mensual",
        "distance_to_station",
        "mean_total",
        "std_total",
        "mean_min",
        "std_min",
        "mean_pic",
        "std_pic",
        "mean_fcs",
        "std_fcs",
        "road_length_m",
    ]
    
    VARIABLES_DISCRETAS_ORDINALES = [
        "n_vialidades",
        "max_carriles",
        "max_nivel",
    ]
    
    VARIABLES_BINARIAS = [
        "both_directions",
        "via_primaria",
        "via_acc_cont",
    ]
    
    def __init__(
        self,
        ps_features: pd.DataFrame,
        grid: 'gpd.GeoDataFrame',
        outcome: pd.DataFrame,
        grid_type: str = 'rectangular',
        grid_size: int = 123,
        drop_columns: list = None
    ):
        self.ps_features = ps_features.copy()
        self.grid = grid.copy()
        self.outcome = outcome.copy()
        self.grid_type = grid_type
        self.grid_size = grid_size
        self.drop_columns = drop_columns
        
        # Atributos para almacenar resultados
        self.propensity_score = None
        self.matching = None
        self.matched_grids = None
        self.smd_df = None
        self.outcome_comparison = None
        self.model = None
    
    def calculate_propensity_score(self):
        """
        Calcula el propensity score usando regresión logística.
        
        El modelo excluye ciertas columnas según el tipo y tamaño del grid para
        mejorar la calidad del matching. Si se especificó drop_columns en
        el constructor, se usa esa lista en lugar del diccionario predefinido.
        """
        if self.drop_columns is not None:
            drop_columns = self.drop_columns
        elif self.grid_type == 'circular':
            # Usar diccionario para grid circular
            drop_columns = self.DROP_COLUMNS_DICT_CIRCULAR.get(
                self.grid_size,
                []  # Por defecto no excluir ninguna columna
            )
        else:
            # Usar diccionario para grid rectangular
            drop_columns = self.DROP_COLUMNS_DICT_RECTANGULAR.get(
                self.grid_size,
                self.DROP_COLUMNS_DICT_RECTANGULAR[123]  # default
            )
        
        # Preparar datos para el modelo
        x = (
            self.ps_features
            .drop(drop_columns, axis=1)
            .set_index('grid_id')
            .drop(columns=['has_camera'])
            .values
        )
        y = self.ps_features.has_camera.values
        
        # Entrenar modelo
        self.model = LogisticRegression()
        self.model.fit(X=x, y=y)
        
        # Calcular propensity scores
        propensity_scores = self.model.predict_proba(x)[:, 1]
        
        self.propensity_score = (
            self.ps_features
            .assign(propensity_score=propensity_scores)
            [['grid_id', 'propensity_score', 'has_camera']]
        )
    
    @staticmethod
    def propensity_score_matching(
        treated_df: pd.DataFrame,
        control_df: pd.DataFrame,
        method: str = "nearest",
        n_matches: int = 1,
        replace: bool = True,
        caliper: float = 0.05
    ) -> dict:
        """
        Realiza matching basado en distancia de propensity score.
        
        Parameters
        ----------
        treated_df : pd.DataFrame
            DataFrame con columnas ["grid_id", "propensity_score"]
        control_df : pd.DataFrame
            DataFrame con columnas ["grid_id", "propensity_score"]
        method : str, default="nearest"
            Método de matching: "nearest" o "caliper"
        n_matches : int, default=1
            Número de matches para cada unidad tratada
        replace : bool, default=True
            Si True, los controles pueden ser emparejados más de una vez
        caliper : float, default=0.05
            Distancia máxima permitida si se usa método "caliper"
        
        Returns
        -------
        dict
            Diccionario {treated_grid_id: [matched_control_grid_ids]}
        """
        # Pre-extraer arrays para velocidad
        treat_ids = treated_df["grid_id"].values
        treat_scores = treated_df["propensity_score"].values
        ctrl_ids = control_df["grid_id"].values
        ctrl_scores = control_df["propensity_score"].values
        
        matches = {}
        
        # Para rastrear qué controles han sido usados si no hay reemplazo
        available = np.ones(len(ctrl_ids), dtype=bool)
        
        for i, (tid, tscore) in enumerate(zip(treat_ids, treat_scores)):
            # Distancias a todos los controles disponibles
            distances = np.abs(ctrl_scores - tscore)
            if not replace:
                distances = np.where(available, distances, np.inf)
            
            if method == "nearest":
                idx = np.argsort(distances)[:n_matches]
                selected_ctrl = ctrl_ids[idx]
                matches[tid] = selected_ctrl.tolist()
                if not replace:
                    available[idx] = False  # Marcar como usados
            elif method == "caliper":
                # Solo controles dentro del caliper
                eligible = (distances <= caliper)
                eligible_idx = np.where(eligible)[0]
                if len(eligible_idx) == 0:
                    matches[tid] = []  # No se encontró match
                    continue
                # Entre los elegibles, elegir los n_matches más cercanos
                eligible_distances = distances[eligible_idx]
                order = np.argsort(eligible_distances)[:n_matches]
                selected_ctrl = ctrl_ids[eligible_idx[order]]
                matches[tid] = selected_ctrl.tolist()
                if not replace:
                    available[eligible_idx[order]] = False
            else:
                raise ValueError("method must be 'nearest' or 'caliper'.")
        
        return matches
    
    def perform_matching(
        self,
        method: str = "nearest",
        n_matches: int = 1,
        replace: bool = False,
        min_controls_in_bin: int = 0,
        n_bins: int = 20
    ):
        """
        Realiza el matching entre unidades tratadas y de control.
        
        Parameters
        ----------
        method : str, default="nearest"
            Método de matching: "nearest" o "caliper"
        n_matches : int, default=1
            Número de matches para cada unidad tratada
        replace : bool, default=False
            Si True, los controles pueden ser emparejados más de una vez
        min_controls_in_bin : int, default=0
            Número mínimo de unidades de control que debe haber en el rango de
            propensity score de una unidad tratada para no ser excluida.
        n_bins : int, default=20
            Número de secciones (bins) en las que se dividirá el rango de
            propensity score para evaluar el min_controls_in_bin.
        """
        if self.propensity_score is None:
            raise ValueError(
                "Debe calcular el propensity score primero usando "
                "calculate_propensity_score()"
            )
        
        control = self.propensity_score[
            self.propensity_score.has_camera == 0
        ]
        treated = self.propensity_score[
            self.propensity_score.has_camera == 1
        ]
        
        if min_controls_in_bin > 0:
            control_scores = control['propensity_score']
            min_ps = control_scores.min()
            max_ps = control_scores.max()
            bins = np.linspace(min_ps, max_ps, n_bins + 1)
            control_counts, _ = np.histogram(control_scores, bins=bins)
            
            valid_treated = []
            for ps in treated['propensity_score']:
                if ps < min_ps or ps > max_ps:
                    valid_treated.append(False)
                    continue
                
                if ps == max_ps:
                    bin_idx = n_bins - 1
                else:
                    bin_idx = np.digitize(ps, bins) - 1
                
                valid_treated.append(control_counts[bin_idx] >= min_controls_in_bin)
                
            treated = treated[valid_treated]
        
        self.matching = self.propensity_score_matching(
            treated_df=treated,
            control_df=control,
            method=method,
            n_matches=n_matches,
            replace=replace
        )
        
        # Filtrar solo aquellos grids que sí están matched
        matched_grid_ids = (
            list(self.matching.keys()) +
            [x for values in self.matching.values() for x in values]
        )
        self.matched_grids = self.ps_features[
            self.ps_features.grid_id.isin(matched_grid_ids)
        ]
    
    @staticmethod
    def smd(treated: np.ndarray, control: np.ndarray) -> float:
        """
        Calcula el Standardized Mean Difference (SMD) entre dos grupos.
        
        La SMD sirve para medir el tamaño del desbalance cuando la variable
        es continua o binaria. SMD < 0.1 implica buen balance.
        
        Parameters
        ----------
        treated : np.ndarray
            Array de valores para el grupo tratado
        control : np.ndarray
            Array de valores para el grupo de control
        
        Returns
        -------
        float
            Valor de SMD
        """
        treated = np.asarray(treated, dtype=float)
        control = np.asarray(control, dtype=float)
        
        # Medias
        mean_t = np.mean(treated)
        mean_c = np.mean(control)
        
        # Desviaciones estándar
        sd_t = np.std(treated, ddof=1)
        sd_c = np.std(control, ddof=1)
        
        # Desviación estándar agrupada
        pooled_sd = np.sqrt((sd_t**2 + sd_c**2) / 2)
        
        # SMD
        if pooled_sd == 0:
            return np.nan  # Evitar división por cero
        
        return (mean_t - mean_c) / pooled_sd
    
    def calculate_smd(self):
        """
        Calcula los valores de SMD antes y después del matching.
        """
        if self.matched_grids is None:
            raise ValueError(
                "Debe realizar el matching primero usando perform_matching()"
            )
        
        def clean_variable(s: str):
            return s.replace('_', ' ').title()
        
        smd_values = []
        all_variables = (
            self.VARIABLES_CONTINUAS +
            self.VARIABLES_DISCRETAS_ORDINALES +
            self.VARIABLES_BINARIAS
        )
        
        # Antes del matching
        treated_bm = self.ps_features[self.ps_features.has_camera == 1]
        control_bm = self.ps_features[self.ps_features.has_camera == 0]
        
        for variable in all_variables:
            if variable not in self.ps_features.columns:
                continue
            var_smd = self.smd(
                treated=treated_bm[variable].values,
                control=control_bm[variable].values
            )
            smd_values.append({
                'variable': clean_variable(variable),
                'smd': var_smd,
                'before_matching': True
            })
        
        # Después del matching
        treated_am = self.matched_grids[self.matched_grids.has_camera == 1]
        control_am = self.matched_grids[self.matched_grids.has_camera == 0]
        
        for variable in all_variables:
            if variable not in self.matched_grids.columns:
                continue
            var_smd = self.smd(
                treated=treated_am[variable].values,
                control=control_am[variable].values
            )
            smd_values.append({
                'variable': clean_variable(variable),
                'smd': var_smd,
                'before_matching': False
            })
        
        self.smd_df = pd.DataFrame(smd_values)
    
    def build_outcome_comparison(self):
        """
        Construye la comparación de tasas de accidentes entre tratamiento y control.
        """
        if self.matched_grids is None:
            raise ValueError(
                "Debe realizar el matching primero usando perform_matching()"
            )
        
        treated_ids = self.matched_grids[
            self.matched_grids.has_camera == 1
        ].grid_id.values
        control_ids = self.matched_grids[
            self.matched_grids.has_camera == 0
        ].grid_id.values
        
        self.outcome_comparison = (
            self.outcome
            .merge(
                self.matched_grids[["grid_id", "has_camera"]],
                on='grid_id'
            )
            .assign(
                grid_type=lambda x: x.has_camera.map({
                    0: "control",
                    1: "treatment"
                })
            )
            .pivot_table(
                index=["timestamp", "volumen_mensual"],
                columns="grid_type",
                values="total",
                aggfunc="sum"
            )
            .reset_index()
            .assign(
                control=lambda x: x.control / x.volumen_mensual,
                treatment=lambda x: x.treatment / x.volumen_mensual,
                change=lambda x: x.treatment / x.control - 1
            )
            .drop("volumen_mensual", axis=1)
            .set_index('timestamp')
            .sort_index()
        )
    
    def plot_smd_comparison(
        self,
        threshold: float = 0.15,
        figsize: tuple = (7, 8),
        save_path: str = None
    ):
        """
        Genera el gráfico de comparación de SMD antes y después del matching.
        
        Parameters
        ----------
        threshold : float, default=0.15
            Umbral para las líneas de referencia en el gráfico
        figsize : tuple, default=(7, 8)
            Tamaño de la figura
        save_path : str, optional
            Ruta donde guardar el gráfico. Si es None, no se guarda.
        
        Returns
        -------
        matplotlib.figure.Figure
            Figura del gráfico
        """
        if self.smd_df is None:
            raise ValueError(
                "Debe calcular SMD primero usando calculate_smd()"
            )
        
        df_before = self.smd_df.query('before_matching')
        df_after = self.smd_df.query('~before_matching')
        
        # Merge ambos dataframes por nombre de variable
        merged = pd.merge(
            df_before[['variable', 'smd']],
            df_after[['variable', 'smd']],
            on='variable',
            suffixes=("_before", "_after")
        )
        
        # Ordenar por máximo SMD absoluto
        merged = merged.copy()
        merged["max_abs_smd"] = merged[
            ["smd_before", "smd_after"]
        ].abs().max(axis=1)
        merged = merged.sort_values("max_abs_smd", ascending=True)
        
        y_labels = merged['variable']
        y_pos = range(len(merged))
        
        fig, ax = plt.subplots(figsize=figsize)

        ax.spines.top.set_visible(False)
        ax.spines.right.set_visible(False)
        ax.spines.bottom.set_visible(False)
        ax.spines.left.set_visible(False)
        
        # Líneas entre before y after
        for i, row in merged.iterrows():
            value_before = row["smd_before"]
            value_after = row["smd_after"]
            better = abs(value_before) > abs(value_after)
            
            ax.plot(
                [value_before, value_after],
                [list(y_pos)[merged.index.get_loc(i)]] * 2,
                linestyle="-",
                color="black" if better else "red",
                alpha=1,
                linewidth=1,
                zorder=1
            )
        
        # Before matching: círculos
        ax.scatter(
            merged["smd_before"], y_pos,
            color="white", edgecolor="black",
            s=80, marker="o", label="Unadjusted", alpha=1,
            linewidth=1, zorder=10
        )
        
        # After matching: círculos
        ax.scatter(
            merged["smd_after"], y_pos,
            color=sns.color_palette("rocket")[0],
            s=80, marker="o", label="Matched", alpha=1, zorder=12
        )
        
        # Líneas de referencia
        ax.axvline(0, color="k", linewidth=1)
        ax.axvline(threshold, color="gray", linestyle="--", lw=1)
        ax.axvline(-threshold, color="gray", linestyle="--", lw=1)
        
        ax.set_yticks(y_pos)
        ax.set_yticklabels(y_labels)
        ax.set_xlabel("Standardized Mean Difference (SMD)")
        ax.set_title(f"SMD Comparison Size {self.grid_size}m")
        ax.legend(loc="lower right", frameon=False)
        ax.grid(axis="y", linestyle=":", alpha=0.3, zorder=-20)
        fig.tight_layout()
        
        if save_path:
            fig.savefig(save_path, dpi=350, transparent=True)
        
        return fig
    
    def plot_outcome_trends(
        self,
        inicio_operaciones: str = "2019-04-22",
        figsize: tuple = (10, 7),
        save_path: str = None
    ):
        """
        Genera el gráfico de tendencias de tasas de accidentes.
        
        Parameters
        ----------
        inicio_operaciones : str, default="2019-04-22"
            Fecha de inicio de operaciones de las cámaras
        figsize : tuple, default=(10, 7)
            Tamaño de la figura
        save_path : str, optional
            Ruta donde guardar el gráfico. Si es None, no se guarda.
        
        Returns
        -------
        matplotlib.figure.Figure
            Figura del gráfico
        """
        if self.outcome_comparison is None:
            raise ValueError(
                "Debe construir la comparación de outcomes primero usando "
                "build_outcome_comparison()"
            )
        
        inicio = pd.to_datetime(inicio_operaciones)
        pdf = self.outcome_comparison
        
        fig, axes = plt.subplots(2, 1, figsize=figsize)
        
        def clean_ax(ax):
            ax.spines.top.set_visible(False)
            ax.spines.right.set_visible(False)
            axis_color = "#495057"
            ax.xaxis.label.set_color(axis_color)
            ax.yaxis.label.set_color(axis_color)
            ax.spines.bottom.set_color(axis_color)
            ax.spines.left.set_color(axis_color)
            ax.tick_params(axis='both', colors=axis_color)
            ax.grid(axis='y', alpha=.2, linestyle=':')
        
        # Primer subplot: Tasas de accidentes
        ax = axes[0]
        clean_ax(ax)
        
        ax.plot(
            pdf.index,
            pdf.control,
            color='#284b63',
            label='Control',
            linewidth=.8,
            linestyle='--'
        )
        
        ax.plot(
            pdf.index,
            pdf.treatment,
            color='#284b63',
            linewidth=1.5,
            alpha=.8,
            label='Treatment'
        )
        
        min_y = pdf.control.min()
        max_y = pdf.control.max()
        ax.vlines(
            x=inicio,
            ymin=min_y, ymax=max_y,
            zorder=-10, color="gray",
            linestyles="dashed",
            linewidth=1, alpha=.4
        )
        
        ax.legend(ncols=2, frameon=False)
        ax.annotate(
            "Inicio\nFotocívicas",
            xy=(inicio + pd.Timedelta(days=30), min_y + (max_y-min_y)*.1),
            ha="left",
            va="top",
            color="darkgray"
        )
        ax.set_title("Tasa de Accidentes Mensual", color='gray')
        ax.set_ylabel("Tasa")
        
        # Segundo subplot: Diferencia porcentual
        ax = axes[1]
        clean_ax(ax)
        
        delta = (pdf.index[1] - pdf.index[0]).days
        width = delta * 0.7
        
        ax.bar(
            pdf.index,
            pdf.change,
            width=width,
            align='center',
            color='#284b63',
            alpha=.8
        )
        
        min_y = pdf.change.min()
        max_y = pdf.change.max()
        ax.vlines(
            x=inicio,
            ymin=min_y, ymax=max_y,
            zorder=-10, color="gray",
            linestyles="dashed",
            linewidth=1, alpha=.4
        )
        ax.annotate(
            "Inicio\nFotocívicas",
            xy=(inicio + pd.Timedelta(days=30), max_y),
            ha="left",
            va="top",
            color="darkgray"
        )
        
        ax.set_title("Diferencia Porcentual\nTratamiento vs Control", color='gray')
        ax.set_ylabel("Diferencia (%)")
        
        fig.tight_layout()
        
        if save_path:
            fig.savefig(save_path, dpi=350, transparent=True)
        
        return fig
    
    def build(
        self,
        matching_method: str = "nearest",
        n_matches: int = 1,
        replace: bool = False,
        min_controls_in_bin: int = 3,
        n_bins: int = 20
    ):
        """
        Ejecuta todo el proceso: calcula PS, realiza matching y evalúa calidad.
        
        Parameters
        ----------
        matching_method : str, default="nearest"
            Método de matching: "nearest" o "caliper"
        n_matches : int, default=1
            Número de matches para cada unidad tratada
        replace : bool, default=False
            Si True, los controles pueden ser emparejados más de una vez
        min_controls_in_bin : int, default=3
            Número mínimo de controles en el bin para no excluir tratamiento.
        n_bins : int, default=20
            Número de bins para soporte común.
        """
        # Calcular propensity score
        self.calculate_propensity_score()
        
        # Realizar matching
        self.perform_matching(
            method=matching_method,
            n_matches=n_matches,
            replace=replace,
            min_controls_in_bin=min_controls_in_bin,
            n_bins=n_bins
        )
        
        # Calcular SMD
        self.calculate_smd()
        
        # Construir comparación de outcomes
        self.build_outcome_comparison()
    
    def get_summary_stats(self) -> dict:
        """
        Retorna estadísticas resumen del matching.
        
        Returns
        -------
        dict
            Diccionario con estadísticas resumen
        """
        if self.matched_grids is None:
            return {}
        
        if self.smd_df is None:
            return {}
        
        treated = self.ps_features[self.ps_features.has_camera == 1]
        control = self.ps_features[self.ps_features.has_camera == 0]
        matched_treated = self.matched_grids[self.matched_grids.has_camera == 1]
        matched_control = self.matched_grids[self.matched_grids.has_camera == 0]
        
        smd_after = self.smd_df.query('~before_matching')
        
        return {
            'unidades_totales': len(self.ps_features),
            'unidades_tratadas': len(treated),
            'unidades_control': len(control),
            'unidades_matched_tratadas': len(matched_treated),
            'unidades_matched_control': len(matched_control),
            'mean_smd_after': smd_after.smd.abs().mean(),
            'sum_smd_after': smd_after.smd.abs().sum()
        }

    def get_common_support_table(self, n_bins: int = 20) -> pd.DataFrame:
        """
        Genera una tabla que demuestra el soporte común (common support) entre
        las unidades de tratamiento y las posibles unidades de control.

        Calcula el rango (min, max) del Propensity Score dentro del grupo de
        control, genera 'n' bins equitativos dentro de ese rango, y cuenta la 
        cantidad de unidades tratadas y de control que caen en cada uno.

        Parameters
        ----------
        n_bins : int, default=20
            Número de secciones (bins) en las que se dividirá el rango.

        Returns
        -------
        pd.DataFrame
            DataFrame con las columnas 'treatment' y 'control', indexadas por el rango 
            de cada bin de propensity score.
        """
        if self.propensity_score is None:
            raise ValueError(
                "Debe calcular el propensity score primero usando "
                "calculate_propensity_score()"
            )

        ps_df = self.propensity_score.copy()
        
        # Filtrar grupos
        control_scores = ps_df[ps_df.has_camera == 0]['propensity_score']
        treated_scores = ps_df[ps_df.has_camera == 1]['propensity_score']
        
        # 1. Encontrar el rango de las unidades de control
        min_ps = control_scores.min()
        max_ps = control_scores.max()
        
        # 2. Configurar los limites exactos en n_bins
        # Se agrega un margen minúsculo arriba y abajo para incluir posibles límites
        bins = np.linspace(min_ps, max_ps, n_bins + 1)
        
        # 3. Asignar las unidades de cada grupo a sus bins
        control_counts, _ = np.histogram(control_scores, bins=bins)
        treated_counts, _ = np.histogram(treated_scores, bins=bins)
        
        # Crear etiquetas legibles para los rangos de los bins
        bin_labels = [
            f"[{bins[i]:.4f}, {bins[i+1]:.4f})"
            if i < len(bins) - 2 
            else f"[{bins[i]:.4f}, {bins[i+1]:.4f}]"  # Último bin es cerrado
            for i in range(len(bins)-1)
        ]
        
        # Crear DataFrame final
        support_df = pd.DataFrame(
            {
                'treatment': treated_counts,
                'control': control_counts
            },
            index=bin_labels
        )
        
        # Agrega las unidades tratadas que quedan fuera del soporte comun de los controles (si las hay)
        treated_above = (treated_scores > max_ps).sum()
        treated_below = (treated_scores < min_ps).sum()
        
        if treated_above > 0 or treated_below > 0:
            out_of_support = pd.DataFrame(
                {
                    'treatment': [treated_below, treated_above],
                    'control': [0, 0]
                },
                index=[
                    f"Out of support (< {min_ps:.4f})",
                    f"Out of support (> {max_ps:.4f})"
                ]
            )
            # Solo añadir si tienen más de 0
            out_of_support = out_of_support[(out_of_support['treatment'] > 0)]
            
            support_df = pd.concat([support_df, out_of_support])
            
        return support_df

    def find_best_drop_columns(
        self,
        max_subset_size: int = None,
        matching_method: str = "nearest",
        n_matches: int = 1,
        replace: bool = False,
        min_controls_in_bin: int = 0,
        n_bins: int = 20
    ) -> dict:
        """
        Encuentra de manera iterativa (fuerza bruta acotada) qué combinación
        de atributos remover para minimizar la suma de SMD absoluto post-matching.
        
        Evalúa todas las combinaciones posibles de variables de exclusión obtenidas
        desde todas las features disponibles en el dataframe.

        Parameters
        ----------
        max_subset_size : int, optional
            Tamaño máximo de la combinación a evaluar. Si es None, evalúa hasta la longitud total de candidatas.
        matching_method : str, default="nearest"
            Método de matching: "nearest" o "caliper".
        n_matches : int, default=1
            Número de matches para cada unidad tratada.
        replace : bool, default=False
            Si True, los controles pueden ser emparejados más de una vez.

        Returns
        -------
        dict
            Diccionario que contiene:
            - 'best_drop_columns': la tupla/lista de la mejor combinación.
            - 'min_smd_sum': la suma del SMD lograda.
            - 'resultados': DataFrame de historial documentando cada experimento.
        """
        import itertools
        from tqdm.auto import tqdm # Para dar feedback en notebooks
        
        # Guarda el drop_columns actual para restaurarlo al final
        original_drop_columns = self.drop_columns

        # Todas las variables disponibles para eliminar
        # Excluir 'grid_id' y 'has_camera' que son identificadores/targets
        valid_candidates = [
            c for c in self.ps_features.columns if c not in ['grid_id', 'has_camera']
        ]

        if max_subset_size is None:
            max_subset_size = len(valid_candidates)

        results = []

        # Genera todas las combinaciones posibles desde 1 hasta max_subset_size
        all_combinations = []
        for r in range(1, max_subset_size + 1):
            all_combinations.extend(itertools.combinations(valid_candidates, r))
            
        print(f"Evaluando {len(all_combinations)} combinaciones postuladas...")

        best_sum_smd = float("inf")
        best_combo = None

        for combo in tqdm(all_combinations, desc="Iterando combinaciones drop_columns"):
            combo_list = list(combo)
            self.drop_columns = combo_list

            try:
                # 1. Calcula Propensity Score temporalmente
                self.calculate_propensity_score()

                # 2. Re-Match
                self.perform_matching(
                    method=matching_method,
                    n_matches=n_matches,
                    replace=replace,
                    min_controls_in_bin=min_controls_in_bin,
                    n_bins=n_bins
                )

                # 3. Calcula la calidad de este matching (SMD)
                self.calculate_smd()
                
                # 4. Suma Absolute SMD de las Post-matching series
                smd_after = self.smd_df.query('~before_matching')['smd'].abs().sum()

                # Guardar trazo de iteracion
                results.append({
                    "drop_columns": combo_list,
                    "sum_smd": smd_after
                })

                # Preservamos si es la mejore encontrada hasta ahora
                if smd_after < best_sum_smd:
                    best_sum_smd = smd_after
                    best_combo = combo_list

            except Exception as e:
                # Omitir si hubo problemas de log-reg por colinealidad fuerte
                pass

        # Restaura a estado incial de su inicializacion base
        self.drop_columns = original_drop_columns
        
        # Opcionalmente recalcula la instancia de clase a la mejor metrica encontrada de manera implicita,
        # O dejarlo limpio. Por el momento solo lo retornamos.
        
        res_df = pd.DataFrame(results).sort_values("sum_smd", ascending=True)

        return {
            "best_drop_columns": best_combo,
            "min_smd_sum": best_sum_smd,
            "resultados": res_df
        }

