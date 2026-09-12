"""
Clase para estimar efectos causales usando diferencia en diferencias.

Esta clase encapsula la funcionalidad del notebook estimating-effects.ipynb,
permitiendo estimar el efecto causal de las cámaras de velocidad sobre los
incidentes viales utilizando el método de diferencia en diferencias (DiD).
Calcula los efectos tanto para el número total de accidentes como para las
tasas, y para diferentes niveles de severidad (total, min, pic, fcs).
"""

import warnings
import pandas as pd
import statsmodels.formula.api as smf

warnings.filterwarnings("ignore")


class EffectEstimation:
    """
    Estimador de efectos causales usando diferencia en diferencias.
    
    Esta clase estima el efecto causal de las cámaras de velocidad sobre
    los incidentes viales utilizando el método de diferencia en diferencias.
    Incluye modelos con y sin efectos fijos.
    
    Parameters
    ----------
    outcome : pandas.DataFrame
        Variables de resultado (accidentes) por grid y tiempo
        (de PSFeaturesBuilder.outcome o PSMatching.outcome)
    matched_grids : pandas.DataFrame
        Grids emparejados que definen las unidades tratadas y de control
        (de PSMatching.matched_grids)
    inicio_operaciones : str or pd.Timestamp, default='2019-04-22'
        Fecha de inicio de operaciones de las cámaras
    
    Attributes
    ----------
    results : dict
        Diccionario anidado con los resultados de las regresiones.
        Estructura: results[outcome_type][variable] = lista de diccionarios
        con coeficientes, errores estándar y valores p
    panel_data : dict
        Diccionario con los datos de panel construidos para cada variable
    models : dict
        Diccionario con los modelos estimados (sin efectos fijos)
    fe_models : dict
        Diccionario con los modelos estimados (con efectos fijos)
    """
    
    def __init__(
        self,
        outcome: pd.DataFrame,
        matched_grids: pd.DataFrame,
        inicio_operaciones: str = '2019-04-22'
    ):
        self.outcome = outcome.copy()
        self.matched_grids = matched_grids.copy()
        self.inicio_operaciones = pd.to_datetime(inicio_operaciones)
        
        # Atributos para almacenar resultados
        self.results = {}
        self.panel_data = {}
        self.models = {}
        self.fe_models = {}
    
    def _get_panel_data(self, variable: str) -> pd.DataFrame:
        """
        Construye el panel data utilizando como outcome la variable especificada.
        
        Parameters
        ----------
        variable : str
            Variable de resultado: 'total', 'min', 'pic', o 'fcs'
        
        Returns
        -------
        pd.DataFrame
            DataFrame con columnas: outcome_total, outcome_tasas, treat,
            post, treat_post, grid_id, timestamp
        """
        panel_data = (
            self.outcome
            .merge(
                self.matched_grids[["grid_id", "has_camera"]],
                on='grid_id'
            )
            .rename({"has_camera": "treat"}, axis=1)
            .assign(
                outcome_total=lambda x: x[variable],
                outcome_tasas=lambda x: x[variable] / x.volumen_mensual,
                post=lambda x: (
                    x.timestamp >= self.inicio_operaciones
                ).astype(int),
                treat_post=lambda x: x.treat * x.post
            )
            [[
                "outcome_total",
                "outcome_tasas",
                "treat",
                "post",
                "treat_post",
                "grid_id",
                "timestamp"
            ]]
        )
        return panel_data
    
    def _estimate_model(
        self,
        outcome_type: str,
        variable: str
    ) -> tuple:
        """
        Estima modelos de diferencia en diferencias para una variable específica.
        
        Parameters
        ----------
        outcome_type : str
            Tipo de outcome: 'total' o 'tasas'
        variable : str
            Variable de resultado: 'total', 'min', 'pic', o 'fcs'
        
        Returns
        -------
        tuple
            Tupla con (modelo_sin_fe, modelo_con_fe)
        """
        # Construir panel data
        panel_data = self._get_panel_data(variable)
        
        # Guardar panel data
        key = f"{outcome_type}_{variable}"
        self.panel_data[key] = panel_data
        
        # Modelo sin efectos fijos
        model = smf.ols(
            formula=f"outcome_{outcome_type} ~ treat + post + treat_post",
            data=panel_data
        ).fit(cov_type="HC1")
        
        # Modelo con efectos fijos
        fe_model = smf.ols(
            formula=(
                f"outcome_{outcome_type} ~ treat_post + "
                "C(grid_id) + C(timestamp)"
            ),
            data=panel_data
        ).fit(
            cov_type="cluster",
            cov_kwds={"groups": panel_data["grid_id"]}
        )
        
        return model, fe_model
    
    def _extract_coefficients(
        self,
        model,
        fe_model,
        coef_order: list = None
    ) -> list:
        """
        Extrae coeficientes, errores estándar y valores p de los modelos.
        
        Parameters
        ----------
        model : statsmodels.regression.linear_model.RegressionResults
            Modelo sin efectos fijos
        fe_model : statsmodels.regression.linear_model.RegressionResults
            Modelo con efectos fijos
        coef_order : list, optional
            Orden de los coeficientes a extraer. Si es None, usa el orden por defecto.
        
        Returns
        -------
        list
            Lista de diccionarios con los resultados
        """
        if coef_order is None:
            coef_order = ["Intercept", "treat", "post", "treat_post"]
        
        result_list = []
        
        for coef_name in coef_order:
            # Coeficiente y SE del modelo sin FE
            if coef_name in model.params.index:
                coef = round(model.params[coef_name], 10)
                se = round(model.bse[coef_name], 10)
                pval = round(model.pvalues[coef_name], 10)
            else:
                coef, se, pval = (float("nan"), float("nan"), float("nan"))
            
            # Solo treat_post tiene estimación en FE (los otros están absorbidos)
            if coef_name == "treat_post":
                pval_fe = fe_model.pvalues.get("treat_post", "")
                if pval_fe != "":
                    pval_fe = round(pval_fe, 10)
            else:
                pval_fe = ""
            
            result_list.append({
                "Coeficiente (err. estándar)": (
                    f"{coef:.4g} ({se:.4g})" if not pd.isna(coef) else "nan"
                ),
                "Valor p": pval,
                "Valor p con efectos fijos": pval_fe
            })
        
        return result_list
    
    def estimate_all(self):
        """
        Estima todos los modelos para todas las combinaciones de outcome y variable.
        
        Los resultados se almacenan en self.results con la estructura:
        results[outcome_type][variable] = lista de diccionarios con resultados
        """
        self.results = {}
        self.models = {}
        self.fe_models = {}
        
        outcome_variables = ["total", "tasas"]
        variables = ["total", "min", "pic", "fcs"]
        
        for outcome_variable in outcome_variables:
            self.results[outcome_variable] = {}
            self.models[outcome_variable] = {}
            self.fe_models[outcome_variable] = {}
            
            for variable in variables:
                # Estimar modelos
                model, fe_model = self._estimate_model(
                    outcome_type=outcome_variable,
                    variable=variable
                )
                
                # Guardar modelos
                self.models[outcome_variable][variable] = model
                self.fe_models[outcome_variable][variable] = fe_model
                
                # Extraer coeficientes
                result_list = self._extract_coefficients(model, fe_model)
                self.results[outcome_variable][variable] = result_list
    
    def get_results_table(
        self,
        outcome_type: str,
        variable: str
    ) -> pd.DataFrame:
        """
        Retorna una tabla con los resultados para una combinación específica.
        
        Parameters
        ----------
        outcome_type : str
            Tipo de outcome: 'total' o 'tasas'
        variable : str
            Variable de resultado: 'total', 'min', 'pic', o 'fcs'
        
        Returns
        -------
        pd.DataFrame
            DataFrame con los resultados formateados
        """
        if outcome_type not in self.results:
            raise ValueError(
                f"outcome_type '{outcome_type}' no encontrado. "
                "Debe ejecutar estimate_all() primero."
            )
        
        if variable not in self.results[outcome_type]:
            raise ValueError(
                f"variable '{variable}' no encontrada para outcome_type "
                f"'{outcome_type}'. Debe ejecutar estimate_all() primero."
            )
        
        result_list = self.results[outcome_type][variable]
        
        # Crear DataFrame
        df = pd.DataFrame(result_list)
        
        # Agregar nombres de coeficientes como índice
        coef_names = ["Intercept", "treat", "post", "treat_post"]
        df.index = coef_names
        
        # Formatear valores p con 5 decimales sin notación científica
        def format_pvalue(val):
            if pd.isna(val) or val == "":
                return val
            return f"{float(val):.5f}"
        
        if "Valor p" in df.columns:
            df["Valor p"] = df["Valor p"].apply(format_pvalue)
        
        if "Valor p con efectos fijos" in df.columns:
            df["Valor p con efectos fijos"] = df["Valor p con efectos fijos"].apply(format_pvalue)
        
        return df
    
    def get_treatment_effect(
        self,
        outcome_type: str = "tasas",
        variable: str = "total"
    ) -> dict:
        """
        Retorna el efecto del tratamiento (treat_post) para una combinación específica.
        
        Parameters
        ----------
        outcome_type : str, default="tasas"
            Tipo de outcome: 'total' o 'tasas'
        variable : str, default="total"
            Variable de resultado: 'total', 'min', 'pic', o 'fcs'
        
        Returns
        -------
        dict
            Diccionario con el coeficiente, error estándar, valor p y valor p con FE
        """
        if outcome_type not in self.models:
            raise ValueError(
                f"outcome_type '{outcome_type}' no encontrado. "
                "Debe ejecutar estimate_all() primero."
            )
        
        if variable not in self.models[outcome_type]:
            raise ValueError(
                f"variable '{variable}' no encontrada. "
                "Debe ejecutar estimate_all() primero."
            )
        
        model = self.models[outcome_type][variable]
        fe_model = self.fe_models[outcome_type][variable]
        
        if "treat_post" not in model.params.index:
            return {
                "coeficiente": None,
                "error_estandar": None,
                "valor_p": None,
                "valor_p_fe": None
            }
        
        return {
            "coeficiente": model.params["treat_post"],
            "error_estandar": model.bse["treat_post"],
            "valor_p": model.pvalues["treat_post"],
            "valor_p_fe": fe_model.pvalues.get("treat_post", None)
        }
    
    def get_all_treatment_effects(self) -> pd.DataFrame:
        """
        Retorna una tabla con todos los efectos del tratamiento.
        
        Returns
        -------
        pd.DataFrame
            DataFrame con los efectos del tratamiento para todas las combinaciones
        """
        results_list = []
        
        outcome_variables = ["total", "tasas"]
        variables = ["total", "min", "pic", "fcs"]
        
        for outcome_type in outcome_variables:
            for variable in variables:
                effect = self.get_treatment_effect(
                    outcome_type=outcome_type,
                    variable=variable
                )
                results_list.append({
                    "outcome_type": outcome_type,
                    "variable": variable,
                    "coeficiente": effect["coeficiente"],
                    "error_estandar": effect["error_estandar"],
                    "valor_p": effect["valor_p"],
                    "valor_p_fe": effect["valor_p_fe"]
                })
        
        return pd.DataFrame(results_list)
    
    def summary(self) -> str:
        """
        Retorna un resumen de los resultados.
        
        Returns
        -------
        str
            String con el resumen de los resultados
        """
        if not self.results:
            return "No se han estimado modelos aún. Ejecute estimate_all() primero."
        
        summary_lines = []
        summary_lines.append("=" * 60)
        summary_lines.append("RESUMEN DE ESTIMACIONES DE EFECTOS")
        summary_lines.append("=" * 60)
        summary_lines.append("")
        
        outcome_variables = ["total", "tasas"]
        variables = ["total", "min", "pic", "fcs"]
        
        for outcome_type in outcome_variables:
            summary_lines.append(f"\nOutcome: {outcome_type.upper()}")
            summary_lines.append("-" * 60)
            
            for variable in variables:
                effect = self.get_treatment_effect(
                    outcome_type=outcome_type,
                    variable=variable
                )
                
                if effect["coeficiente"] is not None:
                    summary_lines.append(
                        f"\n  Variable: {variable.upper()}"
                    )
                    summary_lines.append(
                        f"    Coeficiente: {effect['coeficiente']:.4f}"
                    )
                    summary_lines.append(
                        f"    Error estándar: {effect['error_estandar']:.4f}"
                    )
                    summary_lines.append(
                        f"    Valor p: {effect['valor_p']:.4f}"
                    )
                    if effect["valor_p_fe"] is not None:
                        summary_lines.append(
                            f"    Valor p (FE): {effect['valor_p_fe']:.4f}"
                        )
        
        return "\n".join(summary_lines)

