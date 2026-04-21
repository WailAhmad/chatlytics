"""
Schema Profiler Module
----------------------
Extracts schema definitions and heuristics from a Pandas DataFrame,
with an enhanced 3-Layer Data Profiling engine for the UI.
"""

import pandas as pd
import numpy as np
from typing import Dict, Any

def profile_dataframe(df: pd.DataFrame) -> Dict[str, Any]:
    """Profile a DataFrame and return its schema, types, and smart visual statistics."""
    
    total_rows = len(df)
    total_cells = df.size
    
    # ── LAYER 1: Data Health ──
    missing_count = int(df.isnull().sum().sum())
    dup_count = int(df.duplicated().sum())
    
    health = {
        "row_count": total_rows,
        "column_count": len(df.columns),
        "missing_pct": round((missing_count / total_cells) * 100, 2) if total_cells > 0 else 0,
        "duplicate_pct": round((dup_count / total_rows) * 100, 2) if total_rows > 0 else 0,
    }
    health["quality_score"] = round(100 - health["missing_pct"] - health["duplicate_pct"], 1)

    # ── LAYER 2: Semantic Column Detection ──
    numeric_cols = []
    datetime_cols = []
    categorical_cols = []
    
    detailed_columns = {}
    summary = {}
    unique_values = {}
    anomalies = []
    quality_metrics = [] # New: Array of missingness per column
    
    for col in df.columns:
        series = df[col]
        n_unique = series.nunique()
        ratio = n_unique / total_rows if total_rows > 0 else 0
        c_lower = str(col).lower()
        
        is_dt = pd.api.types.is_datetime64_any_dtype(series)
        is_num = pd.api.types.is_numeric_dtype(series)
        
        col_type = "categorical"
        
        if is_dt:
            col_type = "datetime"
            datetime_cols.append(col)
        elif is_num:
            if ratio < 0.05 or n_unique < 20 or "code" in c_lower or "id" in c_lower or "status" in c_lower:
                col_type = "categorical"
                categorical_cols.append(col)
            else:
                col_type = "numeric"
                numeric_cols.append(col)
        else:
            categorical_cols.append(col)
            
        # Data Quality per column
        missing_col = int(series.isnull().sum())
        missing_pct = round((missing_col / total_rows) * 100, 2) if total_rows > 0 else 0
        quality_metrics.append({
            "name": col,
            "missing": missing_col,
            "missing_pct": missing_pct
        })
            
        # ── LAYER 3: Smart Visual Profiling ──
        profile = {"type": col_type, "missing": missing_col, "missing_pct": missing_pct}
        clean_s = series.dropna()
        
        if col_type == "numeric" and len(clean_s) > 0:
            mean_val = float(clean_s.mean())
            max_val = float(clean_s.max())
            min_val = float(clean_s.min())
            
            Q1 = float(clean_s.quantile(0.25))
            Q3 = float(clean_s.quantile(0.75))
            
            summary[col] = {"mean": mean_val, "max": max_val, "min": min_val}
            
            profile["stats"] = {
                "mean": mean_val,
                "median": float(clean_s.median()),
                "std": float(clean_s.std()),
                "min": min_val,
                "max": max_val,
                "q1": Q1,
                "q3": Q3,
                "skew": float(clean_s.skew()) if len(clean_s) > 2 else 0
            }
            
            # Anomaly Detection using IQR
            IQR = Q3 - Q1
            lower_bound = Q1 - 1.5 * IQR
            upper_bound = Q3 + 1.5 * IQR
            outliers = clean_s[(clean_s < lower_bound) | (clean_s > upper_bound)]
            outlier_count = len(outliers)
            
            if outlier_count > 0:
                anomalies.append({
                    "column": col,
                    "count": outlier_count,
                    "percentage": round((outlier_count / len(clean_s)) * 100, 1),
                    "description": f"Found {outlier_count} unusually high/low values in '{col}' (exceeding standard bounds)."
                })
            
            # Generate Histogram Bins
            try:
                counts, bin_edges = np.histogram(clean_s, bins=10)
                profile["histogram"] = [{"name": f"{bin_edges[i]:.1f}-{bin_edges[i+1]:.1f}", "count": int(counts[i])} for i in range(len(counts))]
            except Exception:
                profile["histogram"] = []
                
            skew = profile["stats"]["skew"]
            if skew > 1:
                profile["insight"] = "Distribution is right-skewed, meaning there are occasional very high spikes."
            elif skew < -1:
                profile["insight"] = "Distribution is left-skewed, meaning values tend to stay high with rare low drops."
            else:
                profile["insight"] = "Values are highly consistent with no extreme directional bias."
                
        elif col_type == "categorical" and len(clean_s) > 0:
            vc = clean_s.value_counts()
            top_vc = vc.head(10)
            dist_data = [{"name": str(val), "count": int(cnt), "percentage": round((cnt / len(clean_s)) * 100, 1)} for val, cnt in top_vc.items()]
            profile["distribution"] = dist_data
            
            unique_values[col] = [str(v) for v in top_vc.index.tolist()]
            
            if len(dist_data) > 0:
                top_pct = sum(d["percentage"] for d in dist_data[:2])
                profile["insight"] = f"Highly concentrated: Top {min(2, len(dist_data))} categories account for {top_pct:.1f}% of all records."
                
        elif col_type == "datetime" and len(clean_s) > 0:
            profile["stats"] = {"min": str(clean_s.min()), "max": str(clean_s.max())}
            try:
                trend = clean_s.dt.date.value_counts().sort_index()
                if len(trend) > 20:
                    trend = trend.iloc[np.linspace(0, len(trend)-1, 20).astype(int)]
                
                peak_date = trend.idxmax()
                low_date = trend.idxmin()
                
                profile["trend"] = [{"name": str(d), "count": int(c)} for d, c in trend.items()]
                profile["insight"] = f"Activity peaked around {peak_date} and was lowest near {low_date}."
            except Exception:
                profile["trend"] = []
                
        detailed_columns[col] = profile

    # Update Health with counts
    health["numeric_count"] = len(numeric_cols)
    health["categorical_count"] = len(categorical_cols)
    health["datetime_count"] = len(datetime_cols)

    # Sort quality metrics by missing pct descending
    quality_metrics.sort(key=lambda x: x["missing_pct"], reverse=True)

    # ── Correlation Analysis ──
    correlations = []
    scatter_plots = []
    
    if len(numeric_cols) > 1:
        try:
            corr_matrix = df[numeric_cols].corr()
            for i in range(len(numeric_cols)):
                for j in range(i+1, len(numeric_cols)):
                    c1, c2 = numeric_cols[i], numeric_cols[j]
                    score = corr_matrix.loc[c1, c2]
                    if pd.notna(score) and abs(score) > 0.4:
                        correlations.append({"col1": c1, "col2": c2, "score": round(float(score), 2)})
            correlations.sort(key=lambda x: abs(x["score"]), reverse=True)
            
            # Generate scatter data for the top correlation
            if len(correlations) > 0:
                top_corr = correlations[0]
                c1 = top_corr["col1"]
                c2 = top_corr["col2"]
                
                # Downsample to 150 points to prevent frontend lag
                sample_df = df[[c1, c2]].dropna()
                if len(sample_df) > 150:
                    sample_df = sample_df.sample(150, random_state=42)
                    
                scatter_data = [{"x": float(row[c1]), "y": float(row[c2])} for _, row in sample_df.iterrows()]
                scatter_plots.append({
                    "col1": c1,
                    "col2": c2,
                    "data": scatter_data
                })
        except Exception:
            pass
            
    # ── Key Takeaways ──
    key_takeaways = []
    if health["quality_score"] > 95:
        key_takeaways.append("Data Health is excellent with high completeness and minimal duplication.")
    elif health["quality_score"] < 80:
        key_takeaways.append(f"Data Health is poor ({health['quality_score']}%). Beware of missing values and duplicates.")
        
    if len(correlations) > 0:
        c = correlations[0]
        direction = "positive" if c["score"] > 0 else "negative"
        key_takeaways.append(f"Strong {direction} correlation ({c['score']}) detected between '{c['col1']}' and '{c['col2']}'.")
        
    if len(anomalies) > 0:
        key_takeaways.append(f"Detected mathematical outliers in {len(anomalies)} numeric columns, requiring potential normalization.")
    else:
        key_takeaways.append("Numeric values are stable with no significant anomalies detected.")

    if len(categorical_cols) > 0:
        top_cat = categorical_cols[0]
        if detailed_columns[top_cat].get("insight"):
            key_takeaways.append(f"For '{top_cat}', {detailed_columns[top_cat]['insight']}")

    # Heuristics for semantic roles (Legacy compatibility for LLM Planner)
    roles = {"load": [], "generation": [], "timestamp": datetime_cols.copy(), "location": [], "asset": [], "status": []}
    for col in df.columns:
        cl = str(col).lower()
        if "load" in cl or "consumption" in cl or "usage" in cl: roles["load"].append(col)
        if "gen" in cl or "output" in cl or "production" in cl: roles["generation"].append(col)
        if "region" in cl or "city" in cl or "location" in cl or "zone" in cl: roles["location"].append(col)
        if "asset" in cl or "device" in cl or "equipment" in cl: roles["asset"].append(col)
        if "status" in cl or "code" in cl or "state" in cl: roles["status"].append(col)

    sample_rows = df.head(3).replace({np.nan: None}).to_dict(orient="records")
    missing = df.isnull().sum().to_dict()

    return {
        "row_count": total_rows,
        "column_count": len(df.columns),
        "columns": df.columns.tolist(),
        "dtypes": {k: str(v) for k, v in df.dtypes.items()},
        "numeric_columns": numeric_cols,
        "datetime_columns": datetime_cols,
        "categorical_columns": categorical_cols,
        "missing_values": missing,
        "unique_values": unique_values,
        "sample_rows": sample_rows,
        "summary": summary,
        "inferred_roles": roles,
        # New Detailed UI UI Profile Data
        "health": health,
        "detailed_columns": detailed_columns,
        "quality_metrics": quality_metrics,
        "correlations": correlations,
        "scatter_plots": scatter_plots,
        "anomalies": anomalies,
        "key_takeaways": key_takeaways
    }
