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
    cloudsBitMask = (1 << 1)
    cloudshadowBitMask = (1 << 3)
    snowBitMask = (1 << 4)

    qaMask = image.select('Fmask').bitwiseAnd(cloudsBitMask).eq(0) \
        .And(image.select('Fmask').bitwiseAnd(cloudshadowBitMask).eq(0)) \
        .And(image.select('Fmask').bitwiseAnd(snowBitMask).eq(0))
    return image.updateMask(qaMask)


class IndexCalculator:
    def ndvi(self, image):
        ndvi = image.normalizedDifference(['B5', 'B4']).rename('ndvi')
        return ndvi

    def ndwi(self, image):
        ndwi = image.normalizedDifference(['B3', 'B5']).rename('ndwi')
        return ndwi

    def mndwi(self, image):
        mndwi = image.normalizedDifference(['B3', 'B6']).rename('mndwi')
        return mndwi

    def evi(self, image):
        evi = image.expression(
            '2.5 * ((NIR - RED) / (NIR + 6 * RED - 7.5 * BLUE + 1))', {
                'NIR': image.select('B5'),
                'RED': image.select('B4'),
                'BLUE': image.select('B2')
            }).float()
        return evi.rename('evi')

    def AWEIsh(self, image):
        AWEIsh = image.expression(
            'BLUE + 2.5 * GREEN - 1.5 * (NIR + SWIR1) - 0.25 * SWIR2', {
                'BLUE': image.select('B2'),
                'GREEN': image.select('B3'),
                'NIR': image.select('B5'),
                'SWIR1': image.select('B6'),
                'SWIR2': image.select('B7')
            }).float()
        return AWEIsh.rename('AWEIsh')

# 影像中很多同一时期的, 用这个函数对同日期影像进行平均
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
        # 尝试进行图像集合的分组和平均操作
        meanImages = ee.ImageCollection(meanImagesList)
        return meanImages
    except ee.EEException as e:
        # 如果发生EEException异常，打印错误并返回一个空的ImageCollection
        print(f"An error occurred during image collection processing: {e}")
        return ee.ImageCollection([])


def process_fire(args, water_data):
    Hylak_id, output_folder, fire_start_time, fire_end_time = args
    output_file_path = os.path.join(output_folder, f"{Hylak_id}.txt")
    if os.path.exists(output_file_path):
        return  # 文件存在，跳过此项

    print(f"Processing fire index: {Hylak_id}")

    def cal_cloud(image):
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
        mndwi = image.normalizedDifference(['B3', 'B6'])
        water_mask = mndwi.gt(0).rename('water_mask')
        updated_image = image.addBands(water_mask)
        return updated_image.updateMask(water_mask)  # 必须更新mask

    # # 导入河流shp文件
    # water_data = gpd.read_file(
    #     r"C:\ning\Home_temp_v3\New_Data_20240920\river_dem_Buffer\river_dem_buffer_2km_1984.shp")

    # 你的处理逻辑...
    # try:
    # 初始化字符串变量用于存储打印信息
    output_string = ""
    # selectedBands = ['B2', 'B3', 'B4', 'B5', 'B6', 'B7']
    selectedBands = ['B2_mean', 'B3_mean', 'B4_mean', 'B5_mean', 'B6_mean', 'B7_mean']

    filtered_gdf = water_data[water_data['Hylak_id'] == Hylak_id]
    if filtered_gdf.iloc[0]['Lake_area'] > 900:
        return
    geometry = geemap.geopandas_to_ee(filtered_gdf)
    start_time = (datetime.strptime(fire_start_time, '%Y-%m-%d') - relativedelta(months=2)).strftime('%Y-%m-%d')
    end_time = (datetime.strptime(fire_end_time, '%Y-%m-%d') + relativedelta(months=2)).strftime('%Y-%m-%d')
    # 定义HLSl30影像集合

    image_collection = (
        ee.ImageCollection("NASA/HLS/HLSL30/v002")
        .filterDate(start_time, end_time)
        .filterBounds(geometry)
        .map(cal_cloud)
        .filter(ee.Filter.lt('cloud_coverage', 0.5))
        .map(maskHls)
        .map(calculateMNDWI)
    )

    # 打印影像数量
    try:
        print(start_time, end_time, image_collection.size().getInfo())
    except ee.ee_exception.EEException as e:
        output_string += "Error: " + str(e) + "\n"
        print("Error:", e)
        # 保存output_string到文本文件中
        with open(output_file_path, 'w') as file:
            file.write(output_string)
        return

    image_collection = process_image_collection(image_collection)

    # 检查返回的image_collection是否为空
    def is_image_collection_empty(image_collection):
        try:
            # 尝试获取集合的大小
            return image_collection.size().getInfo() == 0
        except ee.EEException:
            # 如果发生异常，假设集合为空
            return True

    empty = is_image_collection_empty(image_collection)

    if empty:
        print("The processed image collection is empty, skipping to the next iteration.")
        # 如果为空，则跳过当前迭代
        return

    output_string += "Hylak ID: " + str(Hylak_id) + " ImageNum: " + str(image_collection.size().getInfo()) + "\n"

    # 提取反射率
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

        print(fire_start_time, fire_end_time, Hylak_id, date, median, round(iteration_time, 2))
        if "[0, 0, 0, 0, 0, 0]" in median:
            continue
        output_string += f"{fire_start_time} {fire_end_time} {Hylak_id} {date} {median} {round(iteration_time, 2)}\n"


    # 保存output_string到文本文件中
    with open(output_file_path, 'w') as file:
        file.write(output_string)

    # 如果需要在程序最后打印出文件保存的位置
    print(f"Output saved to {output_file_path}")
    #
    # except Exception as e:
    #     print(f"Error processing fire index {Hylak_id}: {e}")


if __name__ == "__main__":
    os.environ['HTTP_PROXY'] = "http://127.0.0.1:7890"
    os.environ['HTTPS_PROXY'] = "http://127.0.0.1:7890"

    ee.Authenticate()
    ee.Initialize()

    wildfire_data_file = r"/After_Discuss_20240919-NEW预处理\lake预处理\hylak_id_dates.csv"
    wildfire_data = pd.read_csv(wildfire_data_file, low_memory=False)

    data_length = len(wildfire_data)

    output_folder = r'C:\ning\Home_temp_v3\HLS-image\Lake'
    if not os.path.exists(output_folder):
        os.makedirs(output_folder)

    # 读取shp文件一次
    water_data = gpd.read_file(
        r"C:\ning\Home_temp_v3\New_Data_20240920\lake_Buffer\filtered_lakes.shp")

    args_list = [(wildfire_data.iloc[line_idx]['Hylak_id'], output_folder,
                  wildfire_data.iloc[line_idx]['earliest_initialdat'],
                  wildfire_data.iloc[line_idx]['latest_finaldate'])
                 for line_idx in range(data_length)]

    for args in tqdm(args_list, total=len(args_list)):
        process_fire(args, water_data)

    print("All tasks are completed.")