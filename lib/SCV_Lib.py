#!/usr/bin/env python
# coding: utf-8

import os

import numpy as np

import itk
from itk import TubeTK as ttk

import numpy as np

#################
#################
#################
#################
#################
def scv_convert_ctp_to_cta(filenames,report_progress=None,debug=False,
                           output_dir=None):
    if report_progress == None:
        report_progress = print
    filenames.sort()
    num_images = len(filenames)

    base_im = itk.imread(filenames[num_images//2],itk.F)
    base_spacing = base_im.GetSpacing()

    if base_spacing[0] != base_spacing[1] or \
            base_spacing[1] != base_spacing[2]:
        report_progress("Converting CTP: Resampling",0)
        resample = ttk.ResampleImage.New(Input=base_im)
        resample.SetMakeIsotropic(True)
        resample.Update()
        base_iso_im = resample.GetOutput()
        if debug:
            progress_label = "DEBUG: Resampling to "+str(
                base_iso_im.GetSpacing())
            report_progress(progress_label,10)
    else:
        report_progress("Converting CTP: Already isotropic",0)
        base_iso_im = base_im

    progress_percent = 10
    report_progress("Creating mask",progress_percent)

    immath = ttk.ImageMath.New(Input=base_iso_im)
    immath.Blur(1)
    base_blur_im = immath.GetOutput()

    immath.Threshold(150, 800, 1, 0)
    immath.Dilate(10, 1, 0)
    base_mask_im = immath.GetOutputUChar()
    if debug:
        itk.imwrite(base_mask_im, output_dir+"/mask.mha",compression=True)

    base_mask_array = itk.GetArrayViewFromImage(base_mask_im)
    base_mask_array[0:4,:,:] = 0
    sizeZ = base_mask_array.shape[0]
    base_mask_array[sizeZ-4:sizeZ,:,:] = 0
    #No need to update mask0 since mask0Tmp is a view of mask0
    
    mask_obj = itk.ImageMaskSpatialObject[3].New()
    mask_obj.SetImage(base_mask_im)
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

    if output_dir!=None and not os.path.exists(output_dir):
        os.mkdir(output_dir)

    progress_percent = 20
    progress_per_file = 70/num_images
    for imNum in range(num_images):

        progress_percent += progress_per_file
        progress_label = "Registering "+str(imNum)+" of "+str(num_images)
        report_progress(progress_label,progress_percent)

        if imNum != num_images//2:
            imMoving = itk.imread(filenames[imNum],itk.F)
            immath.SetInput(imMoving)
            immath.Blur(1)
            imMovingBlur = immath.GetOutput()
    
            imreg = ttk.RegisterImages[ImageType].New()
            imreg.SetFixedImage(imFixedBlur)
            imreg.SetMovingImage(imMovingBlur)
            imreg.SetRigidMaxIterations(100)
            imreg.SetRegistration("RIGID")
            imreg.SetExpectedOffsetMagnitude(5)
            imreg.SetExpectedRotationMagnitude(0.05)
            imreg.SetFixedImageMaskObject(mask_obj)
            imreg.SetUseEvolutionaryOptimization(False)
            if debug:
                imreg.SetReportProgress(True)
            imreg.Update()
    
            tfm = imreg.GetCurrentMatrixTransform()
            imMovingReg = imreg.ResampleImage("BSPLINE_INTERPOLATION",
                                              imMoving,tfm,-1024)
            if debug and output_dir!=None:
                pname,fname = os.path.split(filenames[imNum])
                itk.imwrite(imMovingReg,output_dir+"/"+fname,
                    compression=True)
    
            imdataTmp = itk.GetArrayFromImage(imMovingReg)

            imdatamax = np.maximum(imdatamax,imdataTmp)
            imdataTmp = np.where(imdataTmp==-1024,imdatamin,imdataTmp)
            imdatamin = np.minimum(imdatamin,imdataTmp)
        elif debug and output_dir!=None:
            imMoving = itk.imread(filenames[imNum],itk.F)
            pname,fname = os.path.split(filenames[imNum])
            itk.imwrite(imMoving,output_dir+"/"+fname,
                compression=True)
    
    
    report_progress("Generating CT, CTA, and CTP",90)

    ct = itk.GetImageFromArray(imdatamin)
    ct.CopyInformation(base_iso_im)

    cta = itk.GetImageFromArray(imdatamax)
    cta.CopyInformation(base_iso_im)

    dsa = itk.GetImageFromArray(imdatamax - imdatamin)
    dsa.CopyInformation(base_iso_im)

    report_progress("Done",100)
    return ct, cta, dsa


#################
#################
#################
#################
#################
def scv_segment_brain_from_cta(cta_image,
                               report_progress=None,
                               debug=False):
    ImageType = itk.Image[itk.F, 3]
    LabelMapType = itk.Image[itk.UC,3]

    report_progress("Threshold",5)
    thresh = ttk.ImageMath.New(Input=cta_image)
    thresh.ReplaceValuesOutsideMaskRange(cta_image,1,6000,0)
    thresh.ReplaceValuesOutsideMaskRange(cta_image,0,600,1)
    cta_tmp = thresh.GetOutput()
    thresh.ReplaceValuesOutsideMaskRange(cta_tmp,0,1,2)
    cta_mask = thresh.GetOutputUChar()

    report_progress("Initial Mask",10)
    maskMath = ttk.ImageMath.New(Input=cta_mask)
    maskMath.Threshold(0,1,0,1)
    maskMath.Erode(15,1,0)
    maskMath.Dilate(20,1,0)
    maskMath.Dilate(12,0,1)
    maskMath.Erode(12,1,0)
    brainSeed = maskMath.GetOutputUChar()
    maskMath.SetInput(cta_mask)
    maskMath.Threshold(2,2,0,1)
    maskMath.Erode(2,1,0)
    maskMath.Dilate(10,1,0)
    maskMath.Erode(7,1,0)
    skullSeed = maskMath.GetOutputUChar()
    maskMath.AddImages(brainSeed,1,2)
    comboSeed = maskMath.GetOutputUChar()

    report_progress("Connected Component",20)
    segmenter = ttk.SegmentConnectedComponentsUsingParzenPDFs[ImageType,
                    LabelMapType].New()
    segmenter.SetFeatureImage( cta_image )
    segmenter.SetInputLabelMap( comboSeed )
    segmenter.SetObjectId( 2 )
    segmenter.AddObjectId( 1 )
    segmenter.SetVoidId( 0 )
    segmenter.SetErodeDilateRadius( 20 )
    segmenter.SetHoleFillIterations( 40 )
    segmenter.Update()
    segmenter.ClassifyImages()
    brainMaskRaw = segmenter.GetOutputLabelMap()

    report_progress("Masking",60)
    maskMath.SetInput(brainMaskRaw)
    maskMath.Threshold(2,2,1,0)
    maskMath.Erode(1,1,0)
    brainMaskRaw2 = maskMath.GetOutputUChar()

    connComp = ttk.SegmentConnectedComponents.New(Input=brainMaskRaw2)
    connComp.SetKeepOnlyLargestComponent(True)
    connComp.Update()
    brainMask = connComp.GetOutput()

    report_progress("Finishing",90)
    cast = itk.CastImageFilter[LabelMapType, ImageType].New()
    cast.SetInput(brainMask)
    cast.Update()
    brainMaskF = cast.GetOutput()

    brainMath = ttk.ImageMath[ImageType,ImageType].New(Input=cta_image)
    brainMath.ReplaceValuesOutsideMaskRange( brainMaskF, 1, 1, 0)
    cta_brain_image = brainMath.GetOutput()

    report_progress("Done",100)
    return cta_brain_image


#################
#################
#################
#################
#################
def scv_enhance_vessels_in_cta(cta_image,
                               cta_roi_image,
                               report_progress=None,
                               debug=False ):
    ImageType = itk.Image[itk.F, 3]
    LabelMapType = itk.Image[itk.UC,3]

    report_progress("Masking",5)
    imMath = ttk.ImageMath.New(Input=cta_roi_image)
    imMath.Threshold( 0.00001, 4000, 1, 0)
    imMath.Erode(10,1,0)
    imBrainMaskErode = imMath.GetOutput()
    imMath.SetInput(cta_roi_image)
    imMath.IntensityWindow(0,300,0,300)
    imMath.ReplaceValuesOutsideMaskRange(imBrainMaskErode,0.5,1.5,0)
    imBrainErode = imMath.GetOutput()

    spacing = cta_image.GetSpacing()[0]

    report_progress("Blurring",10)
    imMath = ttk.ImageMath[ImageType,ImageType].New()
    imMath.SetInput(imBrainErode)
    imMath.Blur(1.5*spacing)
    imBlur = imMath.GetOutput()
    imBlurArray = itk.GetArrayViewFromImage(imBlur)

    report_progress("Generating Seeds",20)
    numSeeds = 15
    seedCoverage = 20
    seedCoord = np.zeros([numSeeds,3])
    for i in range(numSeeds):
        seedCoord[i] = np.unravel_index(np.argmax(imBlurArray,
                           axis=None), imBlurArray.shape)
        indx = [int(seedCoord[i][0]),int(seedCoord[i][1]),
                int(seedCoord[i][2])]
        minX = max(indx[0]-seedCoverage,0)
        maxX = max(indx[0]+seedCoverage,imBlurArray.shape[0])
        minY = max(indx[1]-seedCoverage,0)
        maxY = max(indx[1]+seedCoverage,imBlurArray.shape[1])
        minZ = max(indx[2]-seedCoverage,0)
        maxZ = max(indx[2]+seedCoverage,imBlurArray.shape[2])
        imBlurArray[minX:maxX,minY:maxY,minZ:maxZ]=0
        indx.reverse()
        seedCoord[:][i] = cta_roi_image.TransformIndexToPhysicalPoint(indx)

    report_progress("Segmenting Initial Vessels",30)
    vSeg = ttk.SegmentTubes.New(Input=cta_roi_image)
    vSeg.SetVerbose(True)
    vSeg.SetMinRoundness(0.4)
    vSeg.SetMinCurvature(0.002)
    vSeg.SetRadiusInObjectSpace( 1 )
    for i in range(numSeeds):
        progress_label = "Vessel "+str(i)+" of "+str(numSeeds)
        progress_percent = i/numSeeds*20+30
        report_progress(progress_label,progress_percent)
        vSeg.ExtractTubeInObjectSpace( seedCoord[i], i )
    tubeMaskImage = vSeg.GetTubeMaskImage()

    imMath.SetInput(tubeMaskImage)
    imMath.AddImages(cta_roi_image, 200, 1)
    blendIm = imMath.GetOutput()

    report_progress("Computing Training Mask",50)
    trMask = ttk.ComputeTrainingMask[ImageType,LabelMapType].New()
    trMask.SetInput( tubeMaskImage )
    trMask.SetGap( 4 )
    trMask.SetObjectWidth( 1 )
    trMask.SetNotObjectWidth( 1 )
    trMask.Update()
    fgMask = trMask.GetOutput()

    report_progress("Enhancing Image",70)
    enhancer = ttk.EnhanceTubesUsingDiscriminantAnalysis[ImageType,
                   LabelMapType].New()
    enhancer.AddInput( cta_image )
    enhancer.SetLabelMap( fgMask )
    enhancer.SetRidgeId( 255 )
    enhancer.SetBackgroundId( 128 )
    enhancer.SetUnknownId( 0 )
    enhancer.SetTrainClassifier(True)
    enhancer.SetUseIntensityOnly(True)
    enhancer.SetScales([0.5*spacing,1.5*spacing,4*spacing])
    enhancer.Update()
    enhancer.ClassifyImages()

    report_progress("Finalizing",90)
    cta_vess = itk.SubtractImageFilter(
                  Input1=enhancer.GetClassProbabilityImage(0),
                  Input2=enhancer.GetClassProbabilityImage(1))

    imMath.SetInput(cta_roi_image)
    imMath.Threshold(0.0001,2000,1,0)
    imMath.Erode(2,1,0)
    imBrainE = imMath.GetOutput()

    imMath.SetInput(cta_vess)
    imMath.ReplaceValuesOutsideMaskRange(imBrainE, 1, 1, -0.001)
    cta_roi_vess = imMath.GetOutput()

    report_progress("Done",100)
    return cta_vess, cta_roi_vess


#################
#################
#################
#################
#################
def scv_extract_vessels_from_cta(cta_image,
                                 cta_roi_vessels_image,
                                 report_progress=None,
                                 debug=False,
                                 output_dir=None):
    if output_dir!=None and not os.path.exists(output_dir):
        os.mkdir(output_dir)

    spacing = cta_image.GetSpacing()[0]

    report_progress("Thresholding",5)
    imMath = ttk.ImageMath.New(cta_roi_vessels_image)
    imMath.MedianFilter(1)
    imMath.Threshold(0.00000001, 9999, 1, 0)
    im1VessMask = imMath.GetOutputShort()

    report_progress("Connecting",10)
    ccSeg = ttk.SegmentConnectedComponents.New(im1VessMask)
    ccSeg.SetMinimumVolume(50)
    ccSeg.Update()
    im1VessMaskCC = ccSeg.GetOutput()

    imMathSS = ttk.ImageMath.New(im1VessMaskCC)
    imMathSS.Threshold(0,0,1,0)
    im1VessMaskInv = imMathSS.GetOutputFloat()
    
    report_progress("Filling in",20)
    distFilter = itk.DanielssonDistanceMapImageFilter.New(im1VessMaskInv)
    distFilter.Update()
    dist = distFilter.GetOutput()

    report_progress("Generating seeds",30)
    imMath.SetInput(dist)
    imMath.Blur(0.4*spacing)
    tmp = imMath.GetOutput()
    imMath.ReplaceValuesOutsideMaskRange(tmp, 0.1, 10, 0)
    im1SeedRadius = imMath.GetOutput()
    
    itk.imwrite(im1SeedRadius, output_dir+"/cta_vessel_seed_radius.mha")

    report_progress("Generating input",30)
    imMath.SetInput(cta_image)
    imMath.ReplaceValuesOutsideMaskRange(cta_roi_vessels_image, 0, 1000, 0)
    imMath.Blur(0.4*spacing)
    imMath.IntensityWindow(0.5,300,0,300)
    im1Input = imMath.GetOutput()

    report_progress("Extracting vessels",40)
    vSeg = ttk.SegmentTubes.New(Input=im1Input)
    vSeg.SetVerbose(True)
    vSeg.SetMinCurvature(0)#.0001)
    vSeg.SetMinRoundness(0.02)
    vSeg.SetMinRidgeness(0.5)
    vSeg.SetMinLevelness(0.0)
    vSeg.SetRadiusInObjectSpace( 0.8 )
    vSeg.SetBorderInIndexSpace(3)
    vSeg.SetSeedMask( im1SeedRadius )
    #vSeg.SetSeedRadiusMask( im1SeedRadius )
    vSeg.SetOptimizeRadius(True)
    vSeg.SetUseSeedMaskAsProbabilities(True)
    vSeg.SetSeedExtractionMinimumProbability(0.4)
    vSeg.ProcessSeeds()

    report_progress("Finalizing",90)
    tubeMaskImage = vSeg.GetTubeMaskImage()

    SOWriter = itk.SpatialObjectWriter[3].New()
    SOWriter.SetInput(vSeg.GetTubeGroup())
    SOWriter.SetBinaryPoints(True)
    SOWriter.SetFileName(output_dir+"/cta_vessels.tre")
    SOWriter.Update()

    VTPWriter = itk.WriteTubesAsPolyData.New()
    VTPWriter.SetInput(vSeg.GetTubeGroup())
    VTPWriter.SetFileName(output_dir+"cta_vessels.vtp")
    VTPWriter.Update()

    report_progress("Done",100)
    return tubeMaskImage,vSeg.GetTubeGroup()
