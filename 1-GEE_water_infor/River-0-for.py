import argparse
import concurrent
import math
import os
import random
import sys
import time
from concurrent.futures import ThreadPoolExecutor
from datetime import datetime
from dateutil.relativedelta import relativedelta

import ee
import geemap
import geopandas as gpd
import pandas as pd
from tqdm import tqdm


def maskHls(image):
    # Mask clouds, cloud shadows, and snow in HLS imagery
    cloudsBitMask = (1 << 1)
    cloudshadowBitMask = (1 << 3)
    snowBitMask = (1 << 4)

    qaMask = image.select('Fmask').bitwiseAnd(cloudsBitMask).eq(0) \
        .And(image.select('Fmask').bitwiseAnd(cloudshadowBitMask).eq(0)) \
        .And(image.select('Fmask').bitwiseAnd(snowBitMask).eq(0))
    return image.updateMask(qaMask)


class IndexCalculator:
    def ndvi(self, image):
        # Calculate NDVI
        ndvi = image.normalizedDifference(['B5', 'B4']).rename('ndvi')
        return ndvi

    def ndwi(self, image):
        # Calculate NDWI
        ndwi = image.normalizedDifference(['B3', 'B5']).rename('ndwi')
        return ndwi

    def mndwi(self, image):
        # Calculate MNDWI
        mndwi = image.normalizedDifference(['B3', 'B6']).rename('mndwi')
        return mndwi

    def evi(self, image):
        # Calculate EVI
        evi = image.expression(
            '2.5 * ((NIR - RED) / (NIR + 6 * RED - 7.5 * BLUE + 1))', {
                'NIR': image.select('B5'),
                'RED': image.select('B4'),
                'BLUE': image.select('B2')
            }).float()
        return evi.rename('evi')

    def AWEIsh(self, image):
        # Calculate AWEIsh
        AWEIsh = image.expression(
            'BLUE + 2.5 * GREEN - 1.5 * (NIR + SWIR1) - 0.25 * SWIR2', {
                'BLUE': image.select('B2'),
                'GREEN': image.select('B3'),
                'NIR': image.select('B5'),
                'SWIR1': image.select('B6'),
                'SWIR2': image.select('B7')
            }).float()
        return AWEIsh.rename('AWEIsh')


# Average images taken on the same date
def process_image_collection(image_collection):
    def func_shf(image):
        image = ee.Image(image)
        date = ee.Date(image.get('system:time_start'))
        dateString = date.format('YYYY-MM-dd')
        return image.set('dateString', dateString)

    grouped = image_collection.toList(image_collection.size()).map(func_shf)

    distinctDates_list = []

    def func_gdv(image):
        dateString = ee.Image(image).get('dateString')
        return dateString

    distinctDates_list = grouped.map(func_gdv)

    distinctDates = distinctDates_list.distinct()

    def getMeanImageByDate(dateString):
        imagesOnDate = grouped.filter(ee.Filter.eq('dateString', dateString))
        meanImage = ee.ImageCollection(imagesOnDate).reduce(ee.Reducer.mean())
        return meanImage.set('system:time_start', ee.Date(dateString).millis())

    def func_ssk(dateString):
        meanImage = getMeanImageByDate(dateString)
        return meanImage.set('date', dateString)

    meanImagesList = distinctDates.map(func_ssk)

    try:
        meanImages = ee.ImageCollection(meanImagesList)
        return meanImages
    except ee.EEException as e:
        print(f"An error occurred during image collection processing: {e}")
        return ee.ImageCollection([])


# Process fire-related data for a given reach
def process_fire(args, water_data):
    reach_id, output_folder, fire_start_time, fire_end_time = args
    output_file_path = os.path.join(output_folder, f"{reach_id}.txt")
    if os.path.exists(output_file_path):
        return  # Skip if the file already exists

    print(f"Processing fire index: {reach_id}")

    def cal_cloud(image):
        # Calculate cloud coverage
        cloudsBitMask = (1 << 1)
        cloudshadowBitMask = (1 << 3)
        snowBitMask = (1 << 4)

        qaMask = image.select('Fmask').bitwiseAnd(cloudsBitMask).eq(0) \
            .And(image.select('Fmask').bitwiseAnd(cloudshadowBitMask).eq(0)) \
            .And(image.select('Fmask').bitwiseAnd(snowBitMask).eq(0))
        cloudMask = qaMask.lt(1)
        cloudCoverage = cloudMask.reduceRegion(
            reducer=ee.Reducer.mean(),
            geometry=geometry,
            scale=30,
            maxPixels=1e9,
        )
        return image.set('cloud_coverage', cloudCoverage.get('Fmask'))

    def calculateMNDWI(image):
        # Calculate MNDWI and update mask
        mndwi = image.normalizedDifference(['B3', 'B6'])
        water_mask = mndwi.gt(0).rename('water_mask')
        updated_image = image.addBands(water_mask)
        return updated_image.updateMask(water_mask)

    output_string = ""
    selectedBands = ['B2_mean', 'B3_mean', 'B4_mean', 'B5_mean', 'B6_mean', 'B7_mean']

    filtered_gdf = water_data[water_data['reach_id'] == reach_id]
    geometry = geemap.geopandas_to_ee(filtered_gdf)
    start_time = (datetime.strptime(fire_start_time, '%Y-%m-%d') - relativedelta(months=2)).strftime('%Y-%m-%d')
    end_time = (datetime.strptime(fire_end_time, '%Y-%m-%d') + relativedelta(months=2)).strftime('%Y-%m-%d')

    image_collection = (
        ee.ImageCollection("NASA/HLS/HLSL30/v002")
        .filterDate(start_time, end_time)
        .filterBounds(geometry)
        .map(cal_cloud)
        .filter(ee.Filter.lt('cloud_coverage', 0.5))
        .map(maskHls)
        .map(calculateMNDWI)
    )

    try:
        print(start_time, end_time, image_collection.size().getInfo())
    except ee.ee_exception.EEException as e:
        output_string += "Error: " + str(e) + "\n"
        print("Error:", e)
        with open(output_file_path, 'w') as file:
            file.write(output_string)
        return

    image_collection = process_image_collection(image_collection)

    def is_image_collection_empty(image_collection):
        try:
            return image_collection.size().getInfo() == 0
        except ee.EEException:
            return True

    empty = is_image_collection_empty(image_collection)

    if empty:
        print("The processed image collection is empty. Skipping.")
        return

    output_string += "reach ID: " + str(reach_id) + " ImageNum: " + str(image_collection.size().getInfo()) + "\n"

    for i in range(image_collection.size().getInfo()):
        start_time = time.time()
        image = ee.Image(image_collection.toList(image_collection.size()).get(i)).clip(geometry)
        date = image.get('date').getInfo()

        result_median = image.select(selectedBands).reduceRegion(
            reducer=ee.Reducer.median(),
            geometry=geometry,
            scale=30,
            maxPixels=1e9,
        )

        a = result_median.getInfo()
        try:
            median = [round(value, 4) for value in a.values()]
        except:
            continue
        iteration_time = time.time() - start_time

        print(fire_start_time, fire_end_time, reach_id, date, median, round(iteration_time, 2))
        if "[0, 0, 0, 0, 0, 0]" in median:
            continue
        output_string += f"{fire_start_time} {fire_end_time} {reach_id} {date} {median} {round(iteration_time, 2)}\n"

    with open(output_file_path, 'w') as file:
        file.write(output_string)

    print(f"Output saved to {output_file_path}")


if __name__ == "__main__":
    os.environ['HTTP_PROXY'] = "http://127.0.0.1:7890"
    os.environ['HTTPS_PROXY'] = "http://127.0.0.1:7890"

    ee.Authenticate()
    ee.Initialize()

    wildfire_data_file = r"C:\ning\Home_temp_v3\New_Data_20240920\data\data\reach_id_dates.csv"
    wildfire_data = pd.read_csv(wildfire_data_file, low_memory=False)

    output_folder = r'C:\ning\Home_temp_v3\HLS-image\River'
    if not os.path.exists(output_folder):
        os.makedirs(output_folder)

    water_data = gpd.read_file(
        r"C:\ning\Home_temp_v3\New_Data_20240920\river_dem_Buffer\river_dem_buffer_2km_1984.shp"
    )

    args_list = [
        (
            wildfire_data.iloc[line_idx]['reach_id'],
            output_folder,
            wildfire_data.iloc[line_idx]['earliest_initialdat'],
            wildfire_data.iloc[line_idx]['latest_finaldate'],
        )
        for line_idx in range(len(wildfire_data))
    ]

    for args in tqdm(args_list, total=len(args_list)):
        process_fire(args, water_data)

    print("All tasks are completed.")
