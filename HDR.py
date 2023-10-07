# coding=utf-8
# =============================================================================
# Copyright (c) 2001-2023 FLIR Systems, Inc. All Rights Reserved.
#
# This software is the confidential and proprietary information of FLIR
# Integrated Imaging Solutions, Inc. ("Confidential Information"). You
# shall not disclose such Confidential Information and shall use it only in
# accordance with the terms of the license agreement you entered into
# with FLIR Integrated Imaging Solutions, Inc. (FLIR).
#
# FLIR MAKES NO REPRESENTATIONS OR WARRANTIES ABOUT THE SUITABILITY OF THE
# SOFTWARE, EITHER EXPRESSED OR IMPLIED, INCLUDING, BUT NOT LIMITED TO, THE
# IMPLIED WARRANTIES OF MERCHANTABILITY, FITNESS FOR A PARTICULAR
# PURPOSE, OR NON-INFRINGEMENT. FLIR SHALL NOT BE LIABLE FOR ANY DAMAGES
# SUFFERED BY LICENSEE AS A RESULT OF USING, MODIFYING OR DISTRIBUTING
# THIS SOFTWARE OR ITS DERIVATIVES.
# =============================================================================
#
# Exposure_QuickSpin.py shows how to customize image exposure time
# using the QuickSpin API. QuickSpin is a subset of the Spinnaker library
# that allows for simpler node access and control.
#
# This example prepares the camera, sets a new exposure time, and restores
# the camera to its default state. Ensuring custom values fall within an
# acceptable range is also touched on. Retrieving and setting information
# is the only portion of the example that differs from Exposure.
#
# A much wider range of topics is covered in the full Spinnaker examples than
# in the QuickSpin ones. There are only enough QuickSpin examples to
# demonstrate node access and to get started with the API; please see full
# Spinnaker examples for further or specific knowledge on a topic.
#
# Please leave us feedback at: https://www.surveymonkey.com/r/TDYMVAPI
# More source code examples at: https://github.com/Teledyne-MV/Spinnaker-Examples
# Need help? Check out our forum at: https://teledynevisionsolutions.zendesk.com/hc/en-us/community/topics

import PySpin
import sys
import os
import time
import math
import cv2
import numpy as np
import argparse

# parse arguments
parser = argparse.ArgumentParser(description='Capture HDR images from a camera')
# positional arguments
parser.add_argument('num_images', type=int, help='number of images to capture')
parser.add_argument('dirname', type=str, help='directory to save images')

# optional arguments
parser.add_argument('--gain', type=float, default=1.0, help='gain value to set')
parser.add_argument('--exp_min', type=float, default=30.0, help='minimum exposure time')
parser.add_argument('--exp_max', type=float, default=65000.0, help='maximum exposure time')

args = parser.parse_args()

try:
    os.mkdir(os.path.join(os.path.dirname(os.path.abspath(__file__)), "images"))
except FileExistsError:
    pass
os.chdir(os.path.join(os.path.dirname(os.path.abspath(__file__)), "images"))

NUM_IMAGES = args.num_images

def map_0_1(x, min, max):
    return (x - min) / (max - min)

# define function which will map a x in range 0, 1 to a log scale between min and max
def log_map_0_1(x, min, max):
    return min * math.pow(max / min, x)    


def configure_exposure(cam, exposure: float):
    """
     This function configures a custom exposure time. Automatic exposure is turned
     off in order to allow for the customization, and then the custom setting is
     applied.

     :param cam: Camera to configure exposure for.
     :type cam: CameraPtr
     :return: True if successful, False otherwise.
     :rtype: bool
    """

    print('*** CONFIGURING EXPOSURE ***\n')

    try:
        result = True

        # Turn off automatic exposure mode
        #
        # *** NOTES ***
        # Automatic exposure prevents the manual configuration of exposure
        # times and needs to be turned off for this example. Enumerations
        # representing entry nodes have been added to QuickSpin. This allows
        # for the much easier setting of enumeration nodes to new values.
        #
        # The naming convention of QuickSpin enums is the name of the
        # enumeration node followed by an underscore and the symbolic of
        # the entry node. Selecting "Off" on the "ExposureAuto" node is
        # thus named "ExposureAuto_Off".
        #
        # *** LATER ***
        # Exposure time can be set automatically or manually as needed. This
        # example turns automatic exposure off to set it manually and back
        # on to return the camera to its default state.

        cam.GainAuto.SetValue(PySpin.GainAuto_Off)
        cam.Gain.SetValue(1)
        
        if cam.ExposureAuto.GetAccessMode() != PySpin.RW:
            print('Unable to disable automatic exposure. Aborting...')
            return False

        cam.ExposureAuto.SetValue(PySpin.ExposureAuto_Off)
        print('Automatic exposure disabled...')

        # Set exposure time manually; exposure time recorded in microseconds
        #
        # *** NOTES ***
        # Notice that the node is checked for availability and writability
        # prior to the setting of the node. In QuickSpin, availability and
        # writability are ensured by checking the access mode.
        #
        # Further, it is ensured that the desired exposure time does not exceed
        # the maximum. Exposure time is counted in microseconds - this can be
        # found out either by retrieving the unit with the GetUnit() method or
        # by checking SpinView.

        if cam.ExposureTime.GetAccessMode() != PySpin.RW:
            print('Unable to set exposure time. Aborting...')
            return False
        
        cam_exp_min, cam_exp_max = cam.ExposureTime.GetMin(), cam.ExposureTime.GetMax()
        exp_min = max(cam_exp_min, args.exp_min)
        exp_max = min(cam_exp_max, args.exp_max)
                
        if exposure <= 1:
            exposure = log_map_0_1(exposure, exp_min, exp_max)
        
        exposure = int(exposure)
        
        print(f"Exposure min: {exp_min}, max: {exp_max}, set: {exposure}")

        # Ensure desired exposure time does not exceed the maximum
        exposure_time_to_set = min(cam.ExposureTime.GetMax(), exposure)
        cam.ExposureTime.SetValue(exposure_time_to_set)
        print('Shutter time set to %s us...\n' % exposure_time_to_set)
        
        return int(exposure_time_to_set)

    except PySpin.SpinnakerException as ex:
        print('Error: %s' % ex)
        result = False

    return result


def reset_exposure(cam):
    """
    This function returns the camera to a normal state by re-enabling automatic exposure.

    :param cam: Camera to reset exposure on.
    :type cam: CameraPtr
    :return: True if successful, False otherwise.
    :rtype: bool
    """
    try:
        result = True

        # Turn automatic exposure back on
        #
        # *** NOTES ***
        # Automatic exposure is turned on in order to return the camera to its
        # default state.

        if cam.ExposureAuto.GetAccessMode() != PySpin.RW:
            print('Unable to enable automatic exposure (node retrieval). Non-fatal error...')
            return False

        cam.ExposureAuto.SetValue(PySpin.ExposureAuto_Continuous)

        print('Automatic exposure enabled...')

    except PySpin.SpinnakerException as ex:
        print('Error: %s' % ex)
        result = False

    return result


def print_device_info(cam):
    """
    This function prints the device information of the camera from the transport
    layer; please see NodeMapInfo example for more in-depth comments on printing
    device information from the nodemap.

    :param cam: Camera to get device information from.
    :type cam: CameraPtr
    :return: True if successful, False otherwise.
    :rtype: bool
    """

    print('*** DEVICE INFORMATION ***\n')

    try:
        result = True
        nodemap = cam.GetTLDeviceNodeMap()

        node_device_information = PySpin.CCategoryPtr(nodemap.GetNode('DeviceInformation'))

        if PySpin.IsReadable(node_device_information):
            features = node_device_information.GetFeatures()
            for feature in features:
                node_feature = PySpin.CValuePtr(feature)
                print('%s: %s' % (node_feature.GetName(),
                                  node_feature.ToString() if PySpin.IsReadable(node_feature) else 'Node not readable'))

        else:
            print('Device control information not readable.')

    except PySpin.SpinnakerException as ex:
        print('Error: %s' % ex.message)
        return False

    return result


def acquire_images(cam):
    """
    This function acquires and saves 10 images from a device; please see
    Acquisition example for more in-depth comments on the acquisition of images.

    :param cam: Camera to acquire images from.
    :type cam: CameraPtr
    :return: True if successful, False otherwise.
    :rtype: bool
    """
    print('*** IMAGE ACQUISITION ***')

    try:
        result = True

        # Set acquisition mode to continuous
        if cam.AcquisitionMode.GetAccessMode() != PySpin.RW:
            print('Unable to set acquisition mode to continuous. Aborting...')
            return False

        cam.AcquisitionMode.SetValue(PySpin.AcquisitionMode_Continuous)
        print('Acquisition mode set to continuous...')

        # Begin acquiring images
        cam.BeginAcquisition()

        print('Acquiring images...')

        # Get device serial number for filename
        device_serial_number = ''
        if cam.TLDevice.DeviceSerialNumber is not None and cam.TLDevice.DeviceSerialNumber.GetAccessMode() == PySpin.RO:
            device_serial_number = cam.TLDevice.DeviceSerialNumber.GetValue()

            print('Device serial number retrieved as %s...' % device_serial_number)

        # Get the value of exposure time to set an appropriate timeout for GetNextImage
        timeout = 0
        if cam.ExposureTime.GetAccessMode() == PySpin.RW or cam.ExposureTime.GetAccessMode() == PySpin.RO:
            # The exposure time is retrieved in µs so it needs to be converted to ms to keep consistency with the unit being used in GetNextImage
            timeout = (int)(cam.ExposureTime.GetValue() / 1000 + 1000)
        else:
            print ('Unable to get exposure time. Aborting...')
            return False

        # Retrieve, convert, and save images

        # Create ImageProcessor instance for post processing images
        processor = PySpin.ImageProcessor()

        # Set default image processor color processing method
        #
        # *** NOTES ***
        # By default, if no specific color processing algorithm is set, the image
        # processor will default to NEAREST_NEIGHBOR method.
        processor.SetColorProcessing(PySpin.SPINNAKER_COLOR_PROCESSING_ALGORITHM_HQ_LINEAR)

        for i in range(NUM_IMAGES):
            try:
                # Retrieve next received image and ensure image completion
                # By default, GetNextImage will block indefinitely until an image arrives.
                # In this example, the timeout value is set to [exposure time + 1000]ms to ensure that an image has enough time to arrive under normal conditions
                # change exposure
                exposure = configure_exposure(cam, (i + 1) / (NUM_IMAGES))
                image_result = cam.GetNextImage(timeout)
                image_result = cam.GetNextImage(timeout)
                image_result = cam.GetNextImage(timeout)

                if image_result.IsIncomplete():
                    print('Image incomplete with image status %d...' % image_result.GetImageStatus())

                else:
                    # Print image information
                    width = image_result.GetWidth()
                    height = image_result.GetHeight()
                    print('Grabbed Image %d, width = %d, height = %d' % (i, width, height))

                    # Convert image to Mono8
                    image_converted = processor.Convert(image_result, PySpin.PixelFormat_Mono8)

                    # Create a unique filename
                    filename = f'exp_{exposure}_us.jpg'

                    # Save image
                    image_converted.Save(filename)

                    print('Image saved at %s' % filename)

                # Release image
                image_result.Release()

            except PySpin.SpinnakerException as ex:
                print('Error: %s' % ex)
                result = False

        # End acquisition
        cam.EndAcquisition()

    except PySpin.SpinnakerException as ex:
        print('Error: %s' % ex)
        result = False

    return result


def run_single_camera(cam):
    """
     This function acts as the body of the example; please see NodeMapInfo_QuickSpin example for more
     in-depth comments on setting up cameras.

     :param cam: Camera to run example on.
     :type cam: CameraPtr
     :return: True if successful, False otherwise.
     :rtype: bool
    """
    try:
        # Initialize camera
        cam.Init()

        # Print device info
        result = print_device_info(cam)

        # Acquire images
        result &= acquire_images(cam)

        # Reset exposure
        result &= reset_exposure(cam)

        # Deinitialize camera
        cam.DeInit()

        return result

    except PySpin.SpinnakerException as ex:
        print('Error: %s' % ex)
        return False


def main():
    """
    Example entry point; please see Enumeration_QuickSpin example for more
    in-depth comments on preparing and cleaning up the system.

    :return: True if successful, False otherwise.
    :rtype: bool
    """
    result = True

    # Retrieve singleton reference to system object
    system = PySpin.System.GetInstance()

    # Get current library version
    version = system.GetLibraryVersion()
    print('Library version: %d.%d.%d.%d' % (version.major, version.minor, version.type, version.build))

    # Retrieve list of cameras from the system
    cam_list = system.GetCameras()

    num_cameras = cam_list.GetSize()

    print('Number of cameras detected: %d' % num_cameras)

    # Finish if there are no cameras
    if num_cameras == 0:
        # Clear camera list before releasing system
        cam_list.Clear()

        # Release system instance
        system.ReleaseInstance()

        print('Not enough cameras!')
        input('Done! Press Enter to exit...')
        return False

              
    cam = cam_list.GetByIndex(0)              
    result &= run_single_camera(cam)
    
    # Release reference to camera
    # NOTE: Unlike the C++ examples, we cannot rely on pointer objects being automatically
    # cleaned up when going out of scope.
    # The usage of del is preferred to assigning the variable to None.
    del cam

    # Clear camera list before releasing system
    cam_list.Clear()

    # Release system instance
    system.ReleaseInstance()
    
    return result

def create_HDR():
    # Load images
    image_names = os.listdir(".")
    # image_names = ['exp_30403_us.jpg', 'exp_954_us.jpg', 'exp_44659_us.jpg', 'exp_139_us.jpg', 'exp_95_us.jpg', 'exp_3026_us.jpg', 'exp_64_us.jpg', 'exp_9592_us.jpg', 'exp_14090_us.jpg', 'exp_442_us.jpg', 'exp_205_us.jpg', 'exp_650_us.jpg', 'exp_65601_us.jpg', 'exp_6530_us.jpg', 'exp_44_us.jpg', 'exp_4445_us.jpg', 'exp_301_us.jpg', 'exp_2060_us.jpg', 'exp_1402_us.jpg', 'exp_20697_us.jpg']
    images = [cv2.imread(i) for i in image_names]
    times = np.array([float(i.split("_")[1].split(".")[0]) for i in image_names], dtype=np.float32)
    print(image_names, times)

    # Align images, skip this step if you have portrait EXIF tags
    # alignMTB = cv2.createAlignMTB()
    # alignMTB.process(images, images)

    # Create HDR image
    calibrateDebevec = cv2.createCalibrateDebevec()
    responseDebevec = calibrateDebevec.process(images, times)
    mergeDebevec = cv2.createMergeDebevec()
    hdrDebevec = mergeDebevec.process(images, times, responseDebevec)
    cv2.imwrite('hdr_image.hdr', hdrDebevec)
    print('saved hdr image')
    
    # Tone map the HDR image to convert it to an 8-bit image
    toneMapper = cv2.createTonemap(2)  # 2.2 is a commonly used gamma value
    ldrDebevec = toneMapper.process(hdrDebevec)

    # The result of tone mapping is a float array, we need to convert it to 8-bit
    ldrDebevec_8bit = cv2.normalize(ldrDebevec, None, 0, 255, cv2.NORM_MINMAX)
    ldrDebevec_8bit = np.uint8(ldrDebevec_8bit)

    # Save the 8-bit image as a JPG
    cv2.imwrite('ldr_image.jpg', ldrDebevec_8bit)
    print('saved ldr image')
    
    # Merge images using Exposure Fusion
    mergeMertens = cv2.createMergeMertens()
    fusion = mergeMertens.process(images)

    # The result of mergeMertens.process() is a float array with values in the range [0, 1], so it needs to be normalized to the range [0, 255] for saving as a JPG image
    fusion_8bit = np.clip(fusion*255, 0, 255).astype('uint8')

    # Save the result
    cv2.imwrite('fusion.jpg', fusion_8bit)
    print('saved fusion image')
    

if __name__ == '__main__':
    try: 
        os.mkdir(args.dirname)
    except FileExistsError:
        pass
    os.chdir(args.dirname)
    
    # wipe out all files in the directory
    for f in os.listdir("."):
        os.remove(f)
    
    if main():
        create_HDR()
        sys.exit(0)
    else:
        sys.exit(1)
