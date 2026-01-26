"""
Copyright (C) 2025  Daniel Nelson

    This program is free software: you can redistribute it and/or modify
    it under the terms of the GNU General Public License as published by
    the Free Software Foundation, either version 3 of the License, or
    (at your option) any later version.

    This program is distributed in the hope that it will be useful,
    but WITHOUT ANY WARRANTY; without even the implied warranty of
    MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
    GNU General Public License for more details.

    You should have received a copy of the GNU General Public License
    along with this program.  If not, see <https://www.gnu.org/licenses/>.

"""
import os
import sys
import multiprocessing
import subprocess
import numpy as np
from subprocess import CREATE_NO_WINDOW
from multiprocessing import freeze_support
from os import scandir
from PIL import Image
from PIL.ExifTags import TAGS, GPSTAGS, IFD
from PySide6 import QtCore, QtWidgets, QtGui


file_extensions = (".jpg", ".jpeg", ".tif", ".tiff")


def convert_and_copy(image_p, file_name, out_dir, sdk_dir, em, hum, dist, refl, amb, exif_dir, res):
    print(f"Converting: {file_name}")

    raw_out = os.path.join(out_dir, f"{os.path.splitext(file_name)[0]}.raw")
    tiff_out = os.path.join(out_dir, f"{os.path.splitext(file_name)[0]}.tif")

    sdk_cmd = [
        sdk_dir,
        "-s", image_p,
        "-a", "measure",
        "-o", raw_out,
        "--measurefmt", "float32",
        "--emissivity", str(em),
        "--humidity", str(hum),
        "--distance", str(dist),
        "--reflection", str(refl),
        "--ambient", str(amb)
    ]
    result = subprocess.run(sdk_cmd, stdout=subprocess.PIPE, stderr=subprocess.PIPE,
                            creationflags=CREATE_NO_WINDOW, check=True)
    if result.stderr:
        print(result.stderr.decode().strip())

    try:
        rows, cols = res
        binary_data = np.fromfile(raw_out, dtype=np.float32).reshape((rows, cols))
        pil_image = Image.fromarray(binary_data, mode='F')
        pil_image.save(tiff_out)
    except FileNotFoundError:
        print(f"{raw_out} not found.")

    sdk_cmd_exif = [
        exif_dir,
        "-tagsfromfile", image_p,
        tiff_out
    ]
    result = subprocess.run(sdk_cmd_exif, stdout=subprocess.PIPE, stderr=subprocess.PIPE,
                            creationflags=CREATE_NO_WINDOW, check=True)
    if result.stderr:
        print(result.stderr.decode().strip())

    # Future Add counter for progress and number of files converted
    for f in (raw_out, tiff_out + '_original'):
        try:
            os.remove(f)
        except FileNotFoundError:
            pass


def get_drone_stats(folder_name: str):
    drone_make = ""
    drone_model = ""
    drone_software = ""
    flight_date = ""

    with scandir(folder_name) as it:
        for file in it:
            if file.is_file():
                if file.name.lower().endswith(file_extensions):
                    img = Image.open(file)
                    exif = img.getexif()
                    try:
                        for k, v in exif.items():
                            tag = TAGS.get(k, k)
                            if tag == 'Make':
                                drone_make = v
                            if tag == 'Model':
                                drone_model = v
                            if tag == 'Software':
                                drone_software = v
                            if tag == 'DateTime':
                                flight_date = v
                    except KeyError:
                        pass
                    break

    return drone_make, drone_model, drone_software, flight_date


def get_gps_exif(folder_name: str):
    # This function will be rewritten
    altitudes = []
    num_images = 0

    with scandir(folder_name) as it:
        for file in it:
            if file.is_file():
                if file.name.lower().endswith(file_extensions):
                    num_images += 1
                    gps_dict = {}
                    img = Image.open(file)
                    exif = img.getexif()
                    for ifd_id in IFD:
                        try:
                            ifd = exif.get_ifd(ifd_id)

                            if ifd_id == IFD.GPSInfo:
                                resolve = GPSTAGS
                            else:
                                resolve = TAGS

                            for k, v in ifd.items():
                                tag = resolve.get(k, k)
                                if tag == 'GPSAltitude':
                                    altitudes.append(float(v))
                                    gps_dict.update({"GPSAltitude": float(v)})
                                    gps_dict.update({"id": file.name.replace('.JPG', "").replace('.jpeg', "").replace('.TIF', "")})
                                if tag == 'GPSLatitude':
                                    gps_dict.update({"GPSLatitude": v})
                                if tag == 'GPSLongitude':
                                    gps_dict.update({"GPSLongitude": v})
                                if tag == 'GPSLatitudeRef':
                                    gps_dict.update({"GPSLatitudeRef": v})
                                if tag == 'GPSLongitudeRef':
                                    gps_dict.update({"GPSLongitudeRef": v})
                                # print(tag, v)
                        except KeyError:
                            pass

    alt_min = min(altitudes)
    alt_max = max(altitudes)
    return alt_min, alt_max, num_images


class DroneWidget(QtWidgets.QWidget):
    def __init__(self):
        super().__init__()

        self.button_open = QtWidgets.QPushButton("Open Image Folder")
        self.button_sdk = QtWidgets.QPushButton("Select dji_irp.exe")
        self.button_sdk_exif = QtWidgets.QPushButton("Select exiftool.exe")
        self.button_run = QtWidgets.QPushButton("Convert Thermal Images")

        frame_style = QtWidgets.QFrame.Shadow.Sunken | QtWidgets.QFrame.Shape.Panel

        self.emissivity_box_label = QtWidgets.QLabel()
        self.emissivity_box_label.setFrameStyle(frame_style)
        self.emissivity_box_button = QtWidgets.QPushButton("Set Emissivity")
        self.humidity_box_label = QtWidgets.QLabel()
        self.humidity_box_label.setFrameStyle(frame_style)
        self.humidity_box_button = QtWidgets.QPushButton("Set Humidity")
        self.distance_box_label = QtWidgets.QLabel()
        self.distance_box_label.setFrameStyle(frame_style)
        self.distance_box_button = QtWidgets.QPushButton("Set Altitude")
        self.reflection_box_label = QtWidgets.QLabel()
        self.reflection_box_label.setFrameStyle(frame_style)
        self.reflection_box_button = QtWidgets.QPushButton("Set Reflection Temperature")
        self.ambient_box_label = QtWidgets.QLabel()
        self.ambient_box_label.setFrameStyle(frame_style)
        self.ambient_box_button = QtWidgets.QPushButton("Set Ambient Temperature")

        self.resolution_check_box = QtWidgets.QCheckBox("Infrared Image Super-Resolution Mode")
        self.resolution_check_box.setToolTip(
            "If your images were captured using infrared image super resolution mode they will be size 1280×1024")

        self.dialog_import = QtWidgets.QFileDialog()
        self.dialog_import.setFileMode(QtWidgets.QFileDialog.FileMode.Directory)

        self.dialog_save_loc = QtWidgets.QFileDialog()
        (self.dialog_save_loc.setFileMode(QtWidgets.QFileDialog.FileMode.Directory))

        self.dialog_export = QtWidgets.QFileDialog()
        self.dialog_export.setFileMode(QtWidgets.QFileDialog.FileMode.AnyFile)

        self.dialog_export_exif = QtWidgets.QFileDialog()
        self.dialog_export_exif.setFileMode(QtWidgets.QFileDialog.FileMode.AnyFile)

        self.text_h1 = QtWidgets.QLabel("-Drone Information-", alignment=QtCore.Qt.AlignmentFlag.AlignLeft)
        self.text_make = QtWidgets.QLabel("Drone Make: ", alignment=QtCore.Qt.AlignmentFlag.AlignLeft)
        self.text_model = QtWidgets.QLabel("Drone Model: ", alignment=QtCore.Qt.AlignmentFlag.AlignLeft)
        self.text_soft = QtWidgets.QLabel("Drone Software: ", alignment=QtCore.Qt.AlignmentFlag.AlignLeft)
        self.text_h2 = QtWidgets.QLabel("-Path Information-", alignment=QtCore.Qt.AlignmentFlag.AlignLeft)
        self.text_date = QtWidgets.QLabel("Flight Date: ", alignment=QtCore.Qt.AlignmentFlag.AlignLeft)
        self.text_num_img = QtWidgets.QLabel("Number of Images: ", alignment=QtCore.Qt.AlignmentFlag.AlignLeft)
        self.text_alt_max = QtWidgets.QLabel("Max Altitude: ", alignment=QtCore.Qt.AlignmentFlag.AlignLeft)
        self.text_alt_min = QtWidgets.QLabel("Min Altitude: ", alignment=QtCore.Qt.AlignmentFlag.AlignLeft)

        self.foldername = ""
        self.foldername_out = ""
        self.filename = ""
        self.filename_exif = ""
        self.emissivity = 0.96
        self.humidity = 50
        self.distance = 15
        self.reflection = 20
        self.ambient = 20
        self.sdk_dir = ""
        self.sdk_dir_exif = ""
        self.resolution = 512, 640

        self.layout = QtWidgets.QVBoxLayout(self)
        self.layout.addWidget(self.button_open)
        self.layout.addWidget(self.button_sdk)
        self.layout.addWidget(self.button_sdk_exif)
        self.layout.addWidget(self.button_run)
        self.layout.addWidget(self.emissivity_box_button)
        self.layout.addWidget(self.emissivity_box_label)
        self.layout.addWidget(self.humidity_box_button)
        self.layout.addWidget(self.humidity_box_label)
        self.layout.addWidget(self.distance_box_button)
        self.layout.addWidget(self.distance_box_label)
        self.layout.addWidget(self.reflection_box_button)
        self.layout.addWidget(self.reflection_box_label)
        self.layout.addWidget(self.ambient_box_button)
        self.layout.addWidget(self.ambient_box_label)
        self.layout.addWidget(self.resolution_check_box)
        self.layout.addWidget(self.text_h1)
        self.layout.addWidget(self.text_make)
        self.layout.addWidget(self.text_model)
        self.layout.addWidget(self.text_soft)
        self.layout.addWidget(self.text_h2)
        self.layout.addWidget(self.text_date)
        self.layout.addWidget(self.text_num_img)
        self.layout.addWidget(self.text_alt_max)
        self.layout.addWidget(self.text_alt_min)
        # Future Hide buttons when options are not entered
        # Future Separate GUI from processing threads
        # Future Auto Download dependencies?
        self.button_open.clicked.connect(self.open_import_dir)
        self.button_sdk.clicked.connect(self.open_sdk_dir)
        self.button_sdk_exif.clicked.connect(self.open_sdk_dir_exif)
        self.button_run.clicked.connect(self.open_run)

        self.emissivity_box_button.clicked.connect(self.open_emissivity)
        self.humidity_box_button.clicked.connect(self.open_humidity)
        self.distance_box_button.clicked.connect(self.open_distance)
        self.reflection_box_button.clicked.connect(self.open_reflection)
        self.ambient_box_button.clicked.connect(self.open_ambient)
        self.resolution_check_box.stateChanged.connect(self.set_resolution)

    @QtCore.Slot()
    def open_import_dir(self):
        if self.dialog_import.exec():
            self.foldername = self.dialog_import.selectedUrls()
            self.foldername = self.foldername[0].toString().replace(
                'file:///', '')

        drone_make, drone_model, drone_software, flight_date = get_drone_stats(self.foldername)
        alt_min, alt_max, num_images = get_gps_exif(self.foldername)

        self.text_make.setText("Drone Make: " + drone_make)
        self.text_model.setText("Drone Model: " + drone_model)
        self.text_soft.setText("Drone Software: " + drone_software)
        self.text_date.setText("Flight Date: " + flight_date)
        self.text_num_img.setText("Number of Images: " + str(num_images))
        self.text_alt_max.setText("Max Altitude: " + str(alt_max))
        self.text_alt_min.setText("Min Altitude: " + str(alt_min))

    @QtCore.Slot()
    def open_sdk_dir(self):
        # Get sdk_dir file
        # /dji_thermal_sdk_v1.4_20220929/utility/bin/windows/release_x64/dji_irp.exe
        if self.dialog_export.exec():
            self.filename = self.dialog_export.selectedUrls()
            self.sdk_dir = self.filename[0].toString().replace('file:///', '')
            print(self.sdk_dir)

    @QtCore.Slot()
    def open_sdk_dir_exif(self):
        # Get exiftool file
        if self.dialog_export_exif.exec():
            self.filename_exif = self.dialog_export_exif.selectedUrls()
            self.sdk_dir_exif = self.filename_exif[0].toString().replace('file:///', '')
            print(self.sdk_dir_exif)

    @QtCore.Slot()
    def open_run(self):
        # Open location to save files
        if self.dialog_save_loc.exec():

            self.foldername_out = self.dialog_save_loc.selectedUrls()
            self.foldername_out = self.foldername_out[0].toString().replace(
                'file:///', '')

        image_files = []
        with scandir(self.foldername) as it:
            for file in it:
                if file.is_file():
                    if file.name.lower().endswith(file_extensions):
                        if os.path.splitext(file.name)[0].endswith('_T'):
                            image_files.append(file)

        num_processes = os.cpu_count()
        print("Number of files loaded for conversion: " + str(len(image_files)))
        print("sdk: " + self.sdk_dir)
        print("em: " + str(self.emissivity))
        print("hum: " + str(self.humidity))
        print("distance: " + str(self.distance))
        print("ref: " + str(self.reflection))
        print("ref: " + str(self.ambient))
        print("sdk_dir_exif: " + str(self.sdk_dir_exif))
        print("resolution: " + str(self.resolution))

        with multiprocessing.Pool(processes=num_processes) as pool:
            tasks = [
                (
                    p.path,
                    p.name,
                    self.foldername_out,
                    self.sdk_dir,
                    self.emissivity,
                    self.humidity,
                    self.distance,
                    self.reflection,
                    self.ambient,
                    self.sdk_dir_exif,
                    self.resolution
                )
                for p in image_files
            ]
            print("Run Convert")
            results = pool.starmap(convert_and_copy, tasks)
            pool.close()
            pool.join()
            return [r for r in results if r]

    @QtCore.Slot()
    def open_emissivity(self):
        d, ok = QtWidgets.QInputDialog.getDouble(self, "Enter Emissivity",
                                                 "Emissivity:", 0.96, 0.1, 1.0, 2, step=0.1)
        if ok:
            self.emissivity_box_label.setText(f"{d:g}")
            self.emissivity = d

    @QtCore.Slot()
    def open_humidity(self):
        d, ok = QtWidgets.QInputDialog.getDouble(self, "Enter Humidity",
                                                 "Humidity:", 50, 20, 100, 2, step=1)
        if ok:
            self.humidity_box_label.setText(f"{d:g}%")
            self.humidity = d

    @QtCore.Slot()
    def open_distance(self):
        d, ok = QtWidgets.QInputDialog.getDouble(self, "Enter Altitude",
                                                 "Altitude:", 5, 1, 25, 2, step=1)
        if ok:
            self.distance_box_label.setText(f"{d:g} m")
            self.distance = d

    @QtCore.Slot()
    def open_reflection(self):
        d, ok = QtWidgets.QInputDialog.getDouble(self, "Enter Reflection Temperature",
                                                 "Temperature:", 20, -50, 500, 2, step=1)
        if ok:
            self.reflection_box_label.setText(f"{d:g}°C")
            self.reflection = d

    @QtCore.Slot()
    def open_ambient(self):
        d, ok = QtWidgets.QInputDialog.getDouble(self, "Enter Ambient Temperature",
                                                 "Temperature:", 20, -50, 500, 2, step=1)
        if ok:
            self.ambient_box_label.setText(f"{d:g}°C")
            self.ambient = d

    @QtCore.Slot()
    def set_resolution(self):
        # This function is to handle infrared image super resolution mode for thermal images
        self.resolution = 512, 640
        if self.resolution_check_box.isChecked():
            self.resolution = 1024, 1280


if __name__ == "__main__":
    app = QtWidgets.QApplication([])
    app.setApplicationDisplayName("Drone Thermal Processor")
    # icon_path = os.path.join(sys._MEIPASS, 'Resources/SensorsCpl_1017.ico')
    icon_path = os.path.abspath(os.path.join(os.path.dirname(__file__), 'SensorsCpl_1017.ico'))
    app.setWindowIcon(QtGui.QIcon(icon_path))

    freeze_support()

    widget = DroneWidget()
    widget.resize(400, 600)
    widget.show()

    sys.exit(app.exec())
