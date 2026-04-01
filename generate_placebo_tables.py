import pandas as pd

# Leer los datos
df = pd.read_csv('markdown/data/placebo-effects.csv')

radii = [37.5, 50, 100, 150, 200, 250]
radii_str = ["37.5 m", "50 m", "100 m", "150 m", "200 m", "250 m"]
offsets = [0.5, 1.0, 1.5]
variables = [
    ('total', 'hechos de tránsito generales', 'tab:placebo-general'),
    ('min', 'hechos de tránsito sin lesionados (MIN)', 'tab:placebo-min'),
    ('pic', 'hechos de tránsito con lesionados (PIC)', 'tab:placebo-pic'),
    ('fcs', 'hechos de tránsito con personas fallecidas (FCS)', 'tab:placebo-fcs')
]

def format_number(coef, se, p):
    stars = ""
    if p < 0.01:
        stars = "^{***}"
    elif p < 0.05:
        stars = "^{**}"
    elif p < 0.10:
        stars = "^{*}"
        
    # Scientific notation for very small numbers (tasas)
    if abs(coef) < 0.0001 and coef != 0:
        c_str = f"{coef:.2e}".replace('e-0', '\\times 10^{-').replace('e-', '\\times 10^{-') + "}"
        s_str = f"({se:.2e})".replace('e-0', '\\times 10^{-').replace('e-', '\\times 10^{-') + "}"
        if stars:
            # It's tricky to format sci notation with stars perfectly without a proper math env in text
            return f"${c_str}{stars}$", f"${s_str}$"
        return f"${c_str}$", f"${s_str}$"
    else:
        return f"${coef:.3f}{stars}$", f"$({se:.3f})$"

tex_output = "\\chapter{Apéndice: Pruebas Placebo}\n\\label{chap:pruebas-placebo}\n\n"
tex_output += "\\noindent Este apéndice presenta los resultados de los modelos de diferencias en diferencias utilizando fechas de inicio ficticias (0.5, 1.0 y 1.5 años antes de la implementación real del programa de Fotocívicas). La ausencia de significancia estadística en estos coeficientes de interacción apoya la validez del supuesto de tendencias paralelas.\n\n"

for var_code, var_desc, label in variables:
    tex_output += "\\begin{table}[htbp]\n"
    tex_output += "    \\centering\n"
    tex_output += f"    \\caption{{Resultados de pruebas placebo sobre {var_desc}}}\n"
    tex_output += f"    \\label{{{label}}}\n"
    tex_output += "    \\footnotesize\n"
    tex_output += "    \\begin{adjustbox}{max width=\\textwidth}\n"
    tex_output += "    \\begin{tabular}{l" + "c"*len(radii) + "}\n"
    tex_output += "        \\toprule\n"
    tex_output += "        & " + " & ".join(radii_str) + " \\\\\n"
    tex_output += "        \\midrule\n"
    
    for otype_code, otype_desc in [('total', 'Niveles absolutos'), ('tasas', 'Tasas por 1,000 vehículos')]:
        tex_output += f"        \\multicolumn{{{len(radii)+1}}}{{l}}{{\\textit{{Panel {'A' if otype_code=='total' else 'B'}. {otype_desc}}}}} \\\\\n"
        
        for offset in offsets:
            coefs = []
            ses = []
            for r in radii:
                row = df[(df['variable'] == var_code) & (df['outcome_type'] == otype_code) & (df['radius_size'] == r) & (df['years_offset'] == offset)]
                if not row.empty:
                    c, s = format_number(row.iloc[0]['coeficiente'], row.iloc[0]['error_estandar'], row.iloc[0]['valor_p'])
                    coefs.append(c)
                    ses.append(s)
                else:
                    coefs.append("-")
                    ses.append("-")
            
            tex_output += f"        $T - {offset}$ años & " + " & ".join(coefs) + " \\\\\n"
            tex_output += f"         & " + " & ".join(ses) + " \\\\\n"
        
        if otype_code == 'total':
            tex_output += "        \\midrule\n"
            
    tex_output += "        \\bottomrule\n"
    tex_output += "    \\end{tabular}\n"
    tex_output += "    \\end{adjustbox}\n\n"
    tex_output += "    \\vspace{0.4em}\n"
    tex_output += "    \\begin{minipage}{0.93\\textwidth}\n"
    tex_output += "        \\tiny \\textit{Nota:} Cada coeficiente de la interacción (Tratamiento x Tiempo ficticio) aparece con su error estándar robusto entre paréntesis. ${}^{***} p<0.01$, ${}^{**} p<0.05$, ${}^{*} p<0.10$.\n"
    tex_output += "    \\end{minipage}\n"
    tex_output += "\\end{table}\n\n"
    if var_code != 'fcs':
        tex_output += "\\clearpage\n\n"

with open('Apendices/ApPlacebo.tex', 'w', encoding='utf-8') as f:
    f.write(tex_output)

