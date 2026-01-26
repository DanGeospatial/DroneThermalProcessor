import numpy as np
import subprocess
import os
from PIL import Image
from subprocess import CREATE_NO_WINDOW


em = 0.96
hum = 50
dist = 20
refl = 30

res = 512, 640

file_name = "test.jpg"
image_org = "E:/vid/old_raw/DJI_20240905120125_0001_T.JPG"
out_dir = "E:/vid"

sdk_dir = "E:/vid/dji_thermal_sdk_v1.7_20241205/utility/bin/windows/release_x64/dji_irp.exe"
exif_dir = "E:/vid/exiftool-13.38_64/exiftool.exe"

input_name = file_name.replace(".jpg", "")
raw_out = out_dir + "/" + input_name + ".raw"
tiff_out = out_dir + "/" + input_name + ".tif"


cmd_sdk = f"{sdk_dir} -s {image_org} -a measure -o {raw_out} --measurefmt float32 --emissivity {em} --humidity {hum} --distance {dist} --reflection {refl}"
subprocess.run(cmd_sdk, creationflags=CREATE_NO_WINDOW)

rows, cols = res
binary_data = np.fromfile(raw_out, dtype=np.float32).reshape((rows, cols))

pil_image = Image.fromarray(binary_data, mode="F")
pil_image.save(tiff_out)

cmd_exif = f"{exif_dir} -tagsfromfile {image_org} {tiff_out}"
subprocess.run(cmd_exif, creationflags=CREATE_NO_WINDOW)

os.remove(raw_out)
os.remove(tiff_out + "_original")
