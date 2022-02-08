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
def scv_convert_ctp_to_cta(filenames,report_progress=print,
                           debug=False,
                           output_dir="."):

    filenames.sort()
    num_images = len(filenames)

    base_im = itk.imread(filenames[num_images//2],itk.F)
    base_spacing = base_im.GetSpacing()

    progress_percent = 10
    report_progress("Reading images",progress_percent)

    Dimension = 3
    PixelType = itk.ctype('float')
    ImageType = itk.Image[PixelType,Dimension]

    imdatamax = itk.GetArrayFromImage(base_im)
    imdatamin = imdatamax

    if output_dir!=None and not os.path.exists(output_dir):
        os.mkdir(output_dir)

    progress_percent = 20
    progress_per_file = 70/num_images
    for imNum in range(num_images):
        imMoving = itk.imread(filenames[imNum],itk.F)
        if imMoving.shape != base_im.shape:
            resample = ttk.ResampleImage.New(Input=imMoving)
            resample.SetMatchImage(base_im)
            resample.Update()
            imMovingIso = resample.GetOutput()
            progress_label = "Resampling "+str(imNum)+" of "+str(num_images)
            report_progress(progress_label,progress_percent)
        else:
            imMovingIso = imMoving
        imdataTmp = itk.GetArrayFromImage(imMovingIso)
        imdatamax = np.maximum(imdatamax,imdataTmp)
        imdataTmp = np.where(imdataTmp==-1024,imdatamin,imdataTmp)
        imdatamin = np.minimum(imdatamin,imdataTmp)
        progress_percent += progress_per_file
        progress_label = "Integrating "+str(imNum)+" of "+str(num_images)
        report_progress(progress_label,progress_percent)
    
    report_progress("Generating CT, CTA, and CTP",90)

    ct = itk.GetImageFromArray(imdatamin)
    ct.CopyInformation(base_im)

    cta = itk.GetImageFromArray(imdatamax)
    cta.CopyInformation(base_im)

    diff = imdatamax-imdatamin
    diff[:4,:,:] = 0
    diff[-4:,:,:] = 0
    diff[:,:4,:] = 0
    diff[:,-4:,:] = 0
    diff[:,:,:4] = 0
    diff[:,:,-4:] = 0
    dsa = itk.GetImageFromArray(diff)
    dsa.CopyInformation(base_im)

    report_progress("Done",100)
    return ct,cta,dsa


#################
#################
#################
#################
#################
def scv_segment_brain_from_cta(cta_image,
                               report_progress=print,
                               debug=False):

    ImageType = itk.Image[itk.F,3]
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
    cast = itk.CastImageFilter[LabelMapType,ImageType].New()
    cast.SetInput(brainMask)
    cast.Update()
    brainMaskF = cast.GetOutput()

    brainMath = ttk.ImageMath[ImageType].New(Input=cta_image)
    brainMath.ReplaceValuesOutsideMaskRange( brainMaskF,1,1,0)
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
                               report_progress=print,
                               debug=False ):

    ImageType = itk.Image[itk.F,3]
    LabelMapType = itk.Image[itk.UC,3]

    report_progress("Masking",5)
    imMath = ttk.ImageMath.New(Input=cta_roi_image)
    imMath.Threshold( 0.00001,4000,1,0)
    imMath.Erode(10,1,0)
    imBrainMaskErode = imMath.GetOutput()
    imMath.SetInput(cta_roi_image)
    imMath.IntensityWindow(0,300,0,300)
    imMath.ReplaceValuesOutsideMaskRange(imBrainMaskErode,0.5,1.5,0)
    imBrainErode = imMath.GetOutput()

    spacing = cta_image.GetSpacing()[0]

    report_progress("Blurring",10)
    imMath = ttk.ImageMath[ImageType].New()
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
                           axis=None),imBlurArray.shape)
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
    vSeg.SetVerbose(debug)
    vSeg.SetMinRoundness(0.4)
    vSeg.SetMinCurvature(0.002)
    vSeg.SetRadiusInObjectSpace( 1 )
    for i in range(numSeeds):
        progress_label = "Vessel "+str(i)+" of "+str(numSeeds)
        progress_percent = i/numSeeds*20+30
        report_progress(progress_label,progress_percent)
        vSeg.ExtractTubeInObjectSpace( seedCoord[i],i )
    tubeMaskImage = vSeg.GetTubeMaskImage()

    imMath.SetInput(tubeMaskImage)
    imMath.AddImages(cta_roi_image,200,1)
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
    enhancer.SetScales([0.75*spacing,2*spacing,6*spacing])
    enhancer.Update()
    enhancer.ClassifyImages()

    report_progress("Finalizing",90)
    imMath = ttk.ImageMath[ImageType].New()
    imMath.SetInput(enhancer.GetClassProbabilityImage(0))
    imMath.Blur(0.5*spacing)
    prob0 = imMath.GetOutput()
    imMath.SetInput(enhancer.GetClassProbabilityImage(1))
    imMath.Blur(0.5*spacing)
    prob1 = imMath.GetOutput()
    cta_vess = itk.SubtractImageFilter(Input1=prob0, Input2=prob1)

    imMath.SetInput(cta_roi_image)
    imMath.Threshold(0.0000001,2000,1,0)
    imMath.Erode(2,1,0)
    imBrainE = imMath.GetOutput()

    imMath.SetInput(cta_vess)
    imMath.ReplaceValuesOutsideMaskRange(imBrainE,1,1,-0.001)
    cta_roi_vess = imMath.GetOutput()

    report_progress("Done",100)
    return cta_vess,cta_roi_vess


#################
#################
#################
#################
#################
def scv_extract_vessels_from_cta(cta_image,
                                 cta_roi_vessels_image,
                                 report_progress=print,
                                 debug=False,
                                 output_dir="."):

    if output_dir!=None and not os.path.exists(output_dir):
        os.mkdir(output_dir)

    spacing = cta_image.GetSpacing()[0]

    report_progress("Thresholding",5)
    imMath = ttk.ImageMath.New(cta_roi_vessels_image)
    imMath.MedianFilter(1)
    imMath.Threshold(0.00000001,9999,1,0)
    vess_mask_im = imMath.GetOutputShort()

    if debug and output_dir!=None:
        itk.imwrite(vess_mask_im,
            output_dir+"/extract_vessels_mask.mha",
            compression=True)

    report_progress("Connecting",10)
    ccSeg = ttk.SegmentConnectedComponents.New(vess_mask_im)
    ccSeg.SetMinimumVolume(50)
    ccSeg.Update()
    vess_mask_cc_im = ccSeg.GetOutput()

    if debug and output_dir!=None:
        itk.imwrite(vess_mask_cc_im,
            output_dir+"/extract_vessels_mask_cc.mha",
            compression=True)

    imMathSS = ttk.ImageMath.New(vess_mask_cc_im)
    imMathSS.Threshold(0,0,1,0)
    vess_mask_inv_im = imMathSS.GetOutputFloat()
    
    report_progress("Filling in",20)
    distFilter = itk.DanielssonDistanceMapImageFilter.New(vess_mask_inv_im)
    distFilter.Update()
    dist_map_im = distFilter.GetOutput()

    report_progress("Generating seeds",30)
    imMath.SetInput(dist_map_im)
    imMath.Blur(0.5*spacing)
    tmp = imMath.GetOutput()
    # Distance map's distances are in index units, not spacing
    imMath.ReplaceValuesOutsideMaskRange(tmp,0.333,10,0)
    initial_radius_im = imMath.GetOutput()
    
    if debug and output_dir!=None:
        itk.imwrite(initial_radius_im,
            output_dir+"/vessel_extraction_initial_radius.mha",
            compression=True)

    report_progress("Generating input",30)
    imMath.SetInput(cta_image)
    imMath.ReplaceValuesOutsideMaskRange(cta_roi_vessels_image,0,1000,0)
    imMath.Blur(0.4*spacing)
    imMath.NormalizeMeanStdDev()
    imMath.IntensityWindow(-4,4,0,1000)
    input_im = imMath.GetOutput()

    if debug and output_dir!=None:
        itk.imwrite(input_im,
            output_dir+"/vessel_extraction_input.mha",
            compression=True)

    report_progress("Extracting vessels",40)
    vSeg = ttk.SegmentTubes.New(Input=input_im)
    vSeg.SetVerbose(debug)
    vSeg.SetMinCurvature(0)#.0001)
    vSeg.SetMinRoundness(0.02)
    vSeg.SetMinRidgeness(0.5)
    vSeg.SetMinLevelness(0.0)
    vSeg.SetRadiusInObjectSpace( 0.8*spacing )
    vSeg.SetBorderInIndexSpace(3)
    vSeg.SetSeedMask( initial_radius_im )
    #vSeg.SetSeedRadiusMask( initial_radius_im )
    vSeg.SetOptimizeRadius(True)
    vSeg.SetUseSeedMaskAsProbabilities(True)
    # Performs large-to-small vessel extraction using radius as probability
    vSeg.SetSeedExtractionMinimumProbability(0.99)
    vSeg.ProcessSeeds()

    report_progress("Finalizing",90)
    tubeMaskImage = vSeg.GetTubeMaskImage()

    if debug and output_dir!=None:
        itk.imwrite(tubeMaskImage,
            output_dir+"/vessel_extraction_output.mha",
            compression=True)

    report_progress("Done",100)
    return tubeMaskImage,vSeg.GetTubeGroup()


def scv_register_ctp_images(fixed_image_file,
                        moving_image_files,
                        output_dir,
                        report_progress=print,
                        debug=False):
    ImageType = itk.Image[itk.F,3]

    num_images = len(moving_image_files)
    progress_percent = 10
    progress_per_file = 80/num_images

    fixed_im = itk.imread(fixed_image_file,itk.F)
    fixed_im_spacing = fixed_im.GetSpacing()
    if fixed_im_spacing[0] != fixed_im_spacing[1] or \
       fixed_im_spacing[1] != fixed_im_spacing[2]:
        report_progress("Resampling",10)
        resample = ttk.ResampleImage.New(Input=fixed_im)
        resample.SetMakeIsotropic(True)
        resample.Update()
        fixed_im = resample.GetOutput()
        if debug:
            progress_label = "DEBUG: Resampling to "+str(
                fixed_im.GetSpacing())
            report_progress(progress_label,10)

    imMath = ttk.ImageMath.New(fixed_im)
    imMath.Threshold(150,800,1,0)
    imMath.Dilate(10,1,0)
    mask_im = imMath.GetOutputUChar()
    mask_array = itk.GetArrayViewFromImage(mask_im)
    mask_array[:4,:,:] = 0
    mask_array[-4:,:,:] = 0
    mask_obj = itk.ImageMaskSpatialObject[3].New()
    mask_obj.SetImage(mask_im)
    mask_obj.Update()
    if debug and output_dir!=None:
        itk.imwrite(base_mask_im,
            output_dir+"/mask.mha",
            compression=True)

    for imNum in range(num_images):
        progress_percent += progress_per_file
        progress_label = "Registering "+str(imNum)+" of "+str(num_images)
        report_progress(progress_label,progress_percent)
    
        if moving_image_files[imNum] != fixed_image_file:
            moving_im = itk.imread(moving_image_files[imNum],itk.F)
    
            imreg = ttk.RegisterImages[ImageType].New()
            imreg.SetFixedImage(fixed_im)
            imreg.SetMovingImage(moving_im)
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
            moving_reg_im = imreg.ResampleImage("SINC_INTERPOLATION",
                                                moving_im,tfm,-1024)
            if output_dir!=None:
                pname,fname = os.path.split(moving_image_files[imNum])
                itk.imwrite(moving_reg_im,
                    output_dir+"/"+fname,
                    compression=True)
        elif output_dir!=None:
            pname,fname = os.path.split(moving_image_files[imNum])
            itk.imwrite(fixed_im,
                output_dir+"/"+fname,
                compression=True)

def scv_register_atlas_to_image(atlas_im, atlas_mask_im, in_im):
    ImageType = itk.Image[itk.F,3]

    regAtlasToIn = ttk.RegisterImages[ImageType].New(FixedImage=in_im,
        MovingImage=atlas_im)
    regAtlasToIn.SetReportProgress(True)
    regAtlasToIn.SetRegistration("PIPELINE_AFFINE")
    regAtlasToIn.SetMetric("MATTES_MI_METRIC")
    regAtlasToIn.SetInitialMethodEnum("INIT_WITH_IMAGE_CENTERS")
    regAtlasToIn.Update()
    atlas_reg_im = regAtlasToIn.ResampleImage()
    atlas_mask_reg_im = regAtlasToIn.ResampleImage("NEAREST_NEIGHBOR",
        atlas_mask_im)
    
    return atlas_reg_im,atlas_mask_reg_im

def scv_compute_atlas_region_stats(atlas_im,
                                   time_im,
                                   vess_im,
                                   number_of_time_bins=100,
                                   report_progress=print,
                                   debug=False):

    atlas_arr = itk.GetArrayFromImage(atlas_im)
    time_arr = itk.GetArrayFromImage(time_im)
    vess_arr = itk.GetArrayFromImage(vess_im)

    num_regions = int(atlas_arr.max())
    time_max = time_arr.max()
    time_min = time_arr.min()
    nbins = int(number_of_time_bins)
    time_factor = (time_max-time_min)/(nbins+1)

    bin_value = np.zeros([num_regions,nbins])
    bin_count = np.zeros([num_regions,nbins])

    for atlas_region in range(num_regions):
        report_progress("Masking",(atlas_region+1)*(100/num_regions))
        indx_arr = np.where(atlas_arr==atlas_region)
        indx_list = list(zip(indx_arr[0],indx_arr[1],indx_arr[2]))
        for indx in indx_list:
            time_bin = int((time_arr[indx]-time_min)*time_factor)
            time_bin = min(max(0,time_bin),nbins-1)
            if np.isnan(vess_arr[indx]) == False:
                bin_count[atlas_region,time_bin] += 1
                bin_value[atlas_region,time_bin] += vess_arr[indx]

    bin_label = np.arange(nbins) * time_factor - time_min
    bin_value = np.divide(bin_value,bin_count,where=bin_count!=0)

    report_progress("Done",100)
    return bin_label,bin_value,bin_count
