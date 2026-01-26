import numpy as np
import subprocess
import os
from PIL import Image


em = 0.96
hum = 70
dist = 25
refl = -1

res = 512, 640

file_name = "test.jpg"
image_org = "D:/PaulThermalDrone/20cmIR_85_85_overlap/DJI_20260118191659_0001_T.jpeg"
out_dir = "D:/PaulThermalDrone"

sdk_dir = "Z:/Research/MineRehabClassifications/2023/Thermal Testing/dji_thermal_sdk_v1.8_20250829/utility/bin/windows/release_x64/dji_irp.exe"
exif_dir = "E:/vid/exiftool-13.38_64/exiftool.exe"

input_name = file_name.replace(".jpg", "")
raw_out = out_dir + "/" + input_name + ".raw"
tiff_out = out_dir + "/" + input_name + ".tif"


cmd_sdk = f"{sdk_dir} -s {image_org} -a measure -o {raw_out} --measurefmt float32 --emissivity {em} --humidity {hum} --distance {dist} --reflection {refl}"
subprocess.run(cmd_sdk)


rows, cols = res
binary_data = np.fromfile(raw_out, dtype=np.float32).reshape((rows, cols))

pil_image = Image.fromarray(binary_data, mode="F")
pil_image.save(tiff_out)

cmd_exif = f"{exif_dir} -tagsfromfile {image_org} {tiff_out}"
subprocess.run(cmd_exif)

os.remove(raw_out)
os.remove(tiff_out + "_original")
