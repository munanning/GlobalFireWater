# GlobalFireWater
Essential codes for "Global degradation of water quality caused by fires".

Using remote sensing and machine learning methods, we validated that the increase in fires over the past five years has caused global water quality degradation.

Our project is divided into three main parts:  
1. **Remote Sensing Data Collection (GEE):**  
   Using Google Earth Engine (GEE) to obtain HLS-2 remote sensing images and extract reflectance data of water bodies impacted by fires.  
2. **Machine Learning SSC Retrieval Model:**  
   Building machine learning models to estimate suspended sediment concentration (SSC) based on the collected reflectance data.  
3. **Attribution Analysis Using R:**  
   Performing attribution analysis in R to identify key drivers of water quality degradation, heavily inspired by [RiverMethaneFlux](https://github.com/rocher-ros/RiverMethaneFlux).  

Due to the large scope of this project, many data preprocessing and visualization codes are not detailed or listed. However, researchers in similar fields can use these core codes to quickly develop their own new projects.
