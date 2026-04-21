import pandas as pd
import numpy as np

def profile_dataset(df):
    health = {}
    total_rows = len(df)
    total_cells = df.size
    
    missing_count = int(df.isnull().sum().sum())
    dup_count = int(df.duplicated().sum())
    
    health["row_count"] = total_rows
    health["column_count"] = len(df.columns)
    health["missing_pct"] = round((missing_count / total_cells) * 100, 2) if total_cells else 0
    health["duplicate_pct"] = round((dup_count / total_rows) * 100, 2) if total_rows else 0
    health["quality_score"] = round(100 - health["missing_pct"] - health["duplicate_pct"], 1)

    columns_profile = {}
    numeric_cols = []
    
    for col in df.columns:
        # Avoid processing everything if it's huge, but for now do all
        series = df[col]
        n_unique = series.nunique()
        ratio = n_unique / total_rows if total_rows > 0 else 0
        
        c_lower = col.lower()
        is_dt = pd.api.types.is_datetime64_any_dtype(series)
        is_num = pd.api.types.is_numeric_dtype(series)
        
        col_type = "categorical"
        
        if is_dt:
            col_type = "datetime"
        elif is_num:
            if ratio < 0.05 or n_unique < 20 or "code" in c_lower or "id" in c_lower or "status" in c_lower:
                col_type = "categorical"
            else:
                col_type = "numeric"
                numeric_cols.append(col)
                
        profile = {"type": col_type, "missing": int(series.isnull().sum())}
        
        if col_type == "numeric":
            clean_s = series.dropna()
            if len(clean_s) > 0:
                profile["stats"] = {
                    "mean": float(clean_s.mean()),
                    "median": float(clean_s.median()),
                    "std": float(clean_s.std()),
                    "min": float(clean_s.min()),
                    "max": float(clean_s.max()),
                    "skew": float(clean_s.skew()) if len(clean_s) > 2 else 0
                }
                # Histogram
                counts, bin_edges = np.histogram(clean_s, bins=10)
                hist_data = []
                for i in range(len(counts)):
                    hist_data.append({
                        "bin": f"{bin_edges[i]:.1f} - {bin_edges[i+1]:.1f}",
                        "count": int(counts[i])
                    })
                profile["histogram"] = hist_data
                
                # Simple Insight
                skew = profile["stats"]["skew"]
                if skew > 1:
                    profile["insight"] = "Highly right-skewed distribution, indicating potential high-value outliers."
                elif skew < -1:
                    profile["insight"] = "Highly left-skewed distribution."
                else:
                    profile["insight"] = "Values are relatively symmetrically distributed."
                    
        elif col_type == "categorical":
            clean_s = series.dropna()
            vc = clean_s.value_counts()
            top_vc = vc.head(10)
            dist_data = []
            for val, cnt in top_vc.items():
                dist_data.append({
                    "name": str(val),
                    "count": int(cnt),
                    "percentage": round((cnt / len(clean_s)) * 100, 1) if len(clean_s) else 0
                })
            profile["distribution"] = dist_data
            
            if len(dist_data) > 0:
                top_pct = sum(d["percentage"] for d in dist_data[:2])
                profile["insight"] = f"Top {min(2, len(dist_data))} categories make up {top_pct:.1f}% of the records."
                
        elif col_type == "datetime":
            clean_s = series.dropna()
            if len(clean_s) > 0:
                profile["stats"] = {
                    "min": str(clean_s.min()),
                    "max": str(clean_s.max())
                }
                # Optional: Trend data by grouping by month/day
                # For simplicity, just get value counts by date if possible
                try:
                    trend = clean_s.dt.date.value_counts().sort_index()
                    # Resample or limit to 20 points
                    if len(trend) > 20:
                        trend = trend.iloc[np.linspace(0, len(trend)-1, 20).astype(int)]
                    trend_data = [{"date": str(d), "count": int(c)} for d, c in trend.items()]
                    profile["trend"] = trend_data
                    profile["insight"] = f"Data spans from {profile['stats']['min']} to {profile['stats']['max']}."
                except:
                    pass
                    
        columns_profile[col] = profile

    correlations = []
    if len(numeric_cols) > 1:
        corr_matrix = df[numeric_cols].corr()
        for i in range(len(numeric_cols)):
            for j in range(i+1, len(numeric_cols)):
                c1, c2 = numeric_cols[i], numeric_cols[j]
                score = corr_matrix.loc[c1, c2]
                if pd.notna(score) and abs(score) > 0.4:
                    correlations.append({
                        "col1": c1,
                        "col2": c2,
                        "score": round(float(score), 2)
                    })
        correlations.sort(key=lambda x: abs(x["score"]), reverse=True)

    return {
        "health": health,
        "columns": columns_profile,
        "correlations": correlations
    }

print("Profiler setup complete")
