#!/usr/bin/env python
# coding: utf-8

import numpy as np

import itk
from itk import TubeTK as ttk


def scv_convert_ctp_to_cta( ctp_images ):

    num_images = ctp_images.shape[0]

    base_im = ctp_images[num_images//2])

    resample = ttk.ResampleImage.New(Input=base_im)
    resample.SetMakeIsotropic(True)
    resample.Update()
    base_iso_im = resample.GetOutput()

    immath = ttk.ImageMath.New(Input=base_iso_im)
    immath.Blur(1)
    base_blur_im = immath.GetOutput()

    immath.Threshold(150, 800, 1, 0)
    immath.Dilate(10, 1, 0)
    base_mask_im = immath.GetOutputUChar()

    base_mask_array = itk.GetArrayViewFromImage(base_mask_array)
    base_mask_array[0:4,:,:] = 0
    sizeZ = base_mask_array.shape[0]
    base_mask_array[sizeZ-4:sizeZ,:,:] = 0
    #No need to update mask0 since mask0Tmp is a view of mask0
    
    mask_obj = itk.ImageMaskSpatialObject[3].New()
    mask_obj.SetImage(base_mask_array)
    mask_obj.Update()
    
    Dimension = 3
    PixelType = itk.ctype('float')
    ImageType = itk.Image[PixelType, Dimension]

    imdatamax = itk.GetArrayFromImage(base_iso_im)
    imdatamin = imdatamax
    imdatamax2 = imdatamax
    imdatamin2 = imdatamax
    imdatamax3 = imdatamax
    imdatamin3 = imdatamax

    imFixedBlur = base_blur_im

    for imNum in range(num_images):
        if imNum != num_images//2:
            imMoving = itk.GetImageFromArray(ctp_images[imNum])
            immath.SetInput(imMoving)
            immath.Blur(1)
            imMovingBlur = immath.GetOutput()
    
            imreg = ttk.RegisterImages[ImageType].New()
            imreg.SetFixedImage(imFixedBlur)
            imreg.SetMovingImage(imMovingBlur)
            imreg.SetRigidMaxIterations(3000)
            imreg.SetRegistration("RIGID")
            imreg.SetExpectedOffsetMagnitude(20)
            imreg.SetExpectedRotationMagnitude(0.3)
            #imreg.SetMetric("MEAN_SQUARED_ERROR_METRIC")
            imreg.SetFixedImageMaskObject(maskObj)
            imreg.Update()
    
            tfm = imreg.GetCurrentMatrixTransform()
            imMovingReg = imreg.ResampleImage("LINEAR_INTERPOLATION",
                                              imMoving, tfm, -1024)
    
            imdataTmp = itk.GetArrayFromImage(imMovingReg)
            imdatamax = np.maximum(imdatamax,imdataTmp)
            imdatamin = np.minimum(imdatamin,imdataTmp)
            imdataTmp[np.where(imdataTmp==imdatamax)] = 0
            imdataTmp[np.where(imdataTmp==imdatamin)] = 0
            imdatamax2 = np.maximum(imdatamax2,imdataTmp)
            imdatamin2 = np.minimum(imdatamin2,imdataTmp)
            imdataTmp[np.where(imdataTmp==imdatamax)] = 0
            imdataTmp[np.where(imdataTmp==imdatamin)] = 0
            imdatamax3 = np.maximum(imdatamax3,imdataTmp)
            imdatamin3 = np.minimum(imdatamin3,imdataTmp)
    
    cta = itk.GetImageFromArray(imdatamax3)
    cta.CopyInformation(base_im)

    ct = itk.GetImageFromArray(imdatamin3)
    ct.CopyInformation(base_im)

    dsa = itk.GetImageFromArray(imdatamax3 - imdatamin3)
    dsa.CopyInformation(im0)

    return cta, ct, dsa
