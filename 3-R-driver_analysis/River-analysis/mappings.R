# Mapping of feature names to descriptive labels
feature_name_mapping <- list(
  slope = "Slope (degree)",
  dnbr = "Fire Intensity (dnbr)",
  land_cover = "Land cover (type)",
  wind = "Wind speed (m/s)",
  duration = "Fire duration (days)",
  silt_30 = "Soil silt (% of weight)",
  area = "Fire area (sq.km.)",
  clay_30 = "Soil clay (% of weight)",
  soil_30 = "Soil moisture (% of weight)",
  Rainfall = "Precipitation (mm)",
  koppen_climate = "Koppen climate (type)",
  sand_30 = "Soil sand (% of weight)",
  ndvi = "Vegetation cover (ndvi)",
  max_prec = "Max daily precipitation (mm)",
  max_7_days_sum = "Max 7-day precipitation (mm)",
  first_7_days_sum = "First 7-day precipitation (mm)",
  fire_area_per = "Fire area per basin area (%)",
  slope_basin = "Basin Slope (degree)",
  MIN = "Basin Connectivity (min)",
  MAX = "Basin Connectivity (max)",
  MEAN = "Basin Connectivity (mean)"
)

# Mapping of feature categories
feature_category_mapping <- list(
  `Slope (degree)` = "Connectivity",             # Assign Slope to Connectivity
  `Fire Intensity (dnbr)` = "Fire",
  `Land cover (type)` = "Land cover",
  `Wind speed (m/s)` = "Climate",
  `Fire duration (days)` = "Fire",
  `Soil silt (% of weight)` = "Soil",
  `Fire area (sq.km.)` = "Fire",
  `Soil clay (% of weight)` = "Soil",
  `Soil moisture (% of weight)` = "Soil",
  `Precipitation (mm)` = "Climate",
  `Koppen climate (type)` = "Climate",
  `Soil sand (% of weight)` = "Soil",
  `Vegetation cover (ndvi)` = "Land cover",
  `Max daily precipitation (mm)` = "Climate",
  `Max 7-day precipitation (mm)` = "Climate",
  `First 7-day precipitation (mm)` = "Climate",
  `Fire area per basin area (%)` = "Fire",
  `Basin Slope (degree)` = "Connectivity",      # Assign Basin Slope to Connectivity
  `Basin Connectivity (min)` = "Connectivity",
  `Basin Connectivity (max)` = "Connectivity",
  `Basin Connectivity (mean)` = "Connectivity"
)

# Mapping of categories to colors
category_color_mapping <- list(
  Fire = "brown3",               # or LightCoral
  Connectivity = "gray60",       # or Gray
  Soil = "chocolate",            # or DarkGoldenrod
  Climate = "dodgerblue3",       # or DodgerBlue
  `Land cover` = "forestgreen"   # or LimeGreen
)
