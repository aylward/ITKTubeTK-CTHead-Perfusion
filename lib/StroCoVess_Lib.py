#!/usr/bin/env python
# coding: utf-8

import os
import sys
import subprocess

from pathlib import Path

import csv

import numpy as np

import itk
from itk import TubeTK as tube


def scv_is_bundled():
    return getattr(sys, 'frozen', False) and hasattr(sys, '_MEIPASS')

def scv_get_perfusion_toolbox_path():
    if scv_is_bundled():
        return os.path.join(sys._MEIPASS, 'StroCoVess', 'perfusion_toolbox')
    return os.path.join(os.path.dirname(os.path.realpath(__file__)),
        'perfusion_toolbox')

#################
#################
#################
#################
#################
def scv_convert_ctp_to_cta(filenames,
                           report_progress=print,
                           debug=False,
                           output_dirname="."):

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

    if output_dirname!=None and not os.path.exists(output_dirname):
        os.mkdir(output_dirname)

    progress_percent = 20
    progress_per_file = 70/num_images
    for imNum in range(num_images):
        imMoving = itk.imread(filenames[imNum],itk.F)
        if imMoving.shape != base_im.shape:
            resample = tube.ResampleImage.New(Input=imMoving)
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
def scv_segment_brain_from_ct(ct_image,
                               report_progress=print,
                               debug=False):

    ImageType = itk.Image[itk.F,3]
    LabelMapType = itk.Image[itk.UC,3]

    report_progress("Threshold",5)
    thresh = tube.ImageMath.New(Input=ct_image)
    thresh.IntensityWindow(-50,6000,0,6000)
    imgt = thresh.GetOutput()
    thresh.ReplaceValuesOutsideMaskRange(imgt,1,6000,0)
    thresh.ReplaceValuesOutsideMaskRange(imgt,0,700,1)
    tmpimg = thresh.GetOutput()
    thresh.ReplaceValuesOutsideMaskRange(tmpimg,0,1,2)
    ct_tmp = thresh.GetOutput()

    report_progress("Initial Mask",10)
    maskMath = tube.ImageMath.New(Input=ct_tmp)
    # remove skin
    maskMath.Dilate(15,0,1)
    # shrink brain
    maskMath.Erode(6,2,0)
    # restore skull
    maskMath.ReplaceValueWithinMaskRange(ct_tmp,1,1,0,1)
    # shrink skull
    maskMath.Dilate(3,1,0)
    maskMath.Erode(1,1,0)
    comboSeed = maskMath.GetOutputUChar()
    
    report_progress("Connected Component",20)
    segmenter = tube.SegmentConnectedComponentsUsingParzenPDFs[ImageType,
                    LabelMapType].New()
    segmenter.SetFeatureImage( ct_image )
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

    maskMath = itk.CastImageFilter[LabelMapType, ImageType].New()
    maskMath.SetInput(brainMaskRaw)
    maskMath.Update()
    brainMaskF = maskMath.GetOutput()
    maskMath = tube.ImageMath.New(Input = brainMaskF)
    maskMath.Threshold(2,2,1,0)
    maskMath.Dilate(2,1,0)
    maskMath.Erode(3,1,0)
    brainMaskRaw2 = maskMath.GetOutputUChar()

    connComp = tube.SegmentConnectedComponents.New(Input=brainMaskRaw2)
    connComp.SetKeepOnlyLargestComponent(True)
    connComp.Update()
    brainMask = connComp.GetOutput()

    report_progress("Finishing",90)
    cast = itk.CastImageFilter[LabelMapType,ImageType].New()
    cast.SetInput(brainMask)
    cast.Update()
    brainMaskF = cast.GetOutput()

    brainMath = tube.ImageMath[ImageType].New(Input=ct_image)
    brainMath.ReplaceValuesOutsideMaskRange( brainMaskF,1,1,-1024)
    ct_brain_image = brainMath.GetOutput()

    report_progress("Done",100)
    return ct_brain_image, brainMask


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
    imMath = tube.ImageMath.New(Input=cta_roi_image)
    imMath.Threshold( 0.00001,4000,1,0)
    imMath.Erode(10,1,0)
    imBrainMaskErode = imMath.GetOutput()
    imMath.SetInput(cta_roi_image)
    imMath.IntensityWindow(0,300,0,300)
    imMath.ReplaceValuesOutsideMaskRange(imBrainMaskErode,0.5,1.5,0)
    imBrainErode = imMath.GetOutput()

    spacing = cta_image.GetSpacing()[0]

    report_progress("Blurring",10)
    imMath = tube.ImageMath[ImageType].New()
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
    vSeg = tube.SegmentTubes.New(Input=cta_roi_image)
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
    trMask = tube.ComputeTrainingMask[ImageType,LabelMapType].New()
    trMask.SetInput( tubeMaskImage )
    trMask.SetGap( 4 )
    trMask.SetObjectWidth( 1 )
    trMask.SetNotObjectWidth( 1 )
    trMask.Update()
    fgMask = trMask.GetOutput()

    report_progress("Enhancing Image",70)
    enhancer = tube.EnhanceTubesUsingDiscriminantAnalysis[ImageType,
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
    imMath = tube.ImageMath[ImageType].New()
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
                                 output_dirname="."):

    if output_dirname!=None and not os.path.exists(output_dirname):
        os.mkdir(output_dirname)

    spacing = cta_image.GetSpacing()[0]

    report_progress("Thresholding",5)
    imMath = tube.ImageMath.New(cta_roi_vessels_image)
    imMath.MedianFilter(1)
    imMath.Threshold(0.00000001,9999,1,0)
    vess_mask_im = imMath.GetOutputShort()

    if debug and output_dirname!=None:
        itk.imwrite(vess_mask_im,
            output_dirname+"/extract_vessels_mask.mha",
            compression=True)

    report_progress("Connecting",10)
    ccSeg = tube.SegmentConnectedComponents.New(vess_mask_im)
    ccSeg.SetMinimumVolume(50)
    ccSeg.Update()
    vess_mask_cc_im = ccSeg.GetOutput()

    if debug and output_dirname!=None:
        itk.imwrite(vess_mask_cc_im,
            output_dirname+"/extract_vessels_mask_cc.mha",
            compression=True)

    imMathSS = tube.ImageMath.New(vess_mask_cc_im)
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
    
    if debug and output_dirname!=None:
        itk.imwrite(initial_radius_im,
            output_dirname+"/vessel_extraction_initial_radius.mha",
            compression=True)

    report_progress("Generating input",30)
    imMath.SetInput(cta_image)
    imMath.ReplaceValuesOutsideMaskRange(cta_roi_vessels_image,0,1000,0)
    imMath.Blur(0.4*spacing)
    imMath.NormalizeMeanStdDev()
    imMath.IntensityWindow(-4,4,0,1000)
    input_im = imMath.GetOutput()

    if debug and output_dirname!=None:
        itk.imwrite(input_im,
            output_dirname+"/vessel_extraction_input.mha",
            compression=True)

    report_progress("Extracting vessels",40)
    vSeg = tube.SegmentTubes.New(Input=input_im)
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

    if debug and output_dirname!=None:
        itk.imwrite(tubeMaskImage,
            output_dirname+"/vessel_extraction_output.mha",
            compression=True)

    report_progress("Done",100)
    return tubeMaskImage,vSeg.GetTubeGroup()

#################
#################
#################
#################
#################
def scv_register_ctp_images(fixed_image_filename,
                        moving_image_filenames,
                        output_dirname,
                        report_progress=print,
                        debug=False):
    ImageType = itk.Image[itk.F,3]

    num_images = len(moving_image_filenames)
    progress_percent = 10
    progress_per_file = 70/num_images

    fixed_im = itk.imread(fixed_image_filename,itk.F)
    fixed_im_spacing = fixed_im.GetSpacing()
    if fixed_im_spacing[0] != fixed_im_spacing[1] or \
       fixed_im_spacing[1] != fixed_im_spacing[2]:
        report_progress("Resampling",progress_percent)
        resample = tube.ResampleImage.New(Input=fixed_im)
        resample.SetMakeIsotropic(True)
        resample.Update()
        fixed_im = resample.GetOutput()
        if debug:
            progress_label = "DEBUG: Resampling to "+str(
                fixed_im.GetSpacing())
            report_progress(progress_label,progress_percent)

    imMath = tube.ImageMath.New(fixed_im)
    imMath.Threshold(150,800,1,0)
    imMath.Dilate(10,1,0)
    mask_im = imMath.GetOutputUChar()
    mask_array = itk.GetArrayViewFromImage(mask_im)
    mask_array[:4,:,:] = 0
    mask_array[-4:,:,:] = 0
    mask_obj = itk.ImageMaskSpatialObject[3].New()
    mask_obj.SetImage(mask_im)
    mask_obj.Update()

    for imNum in range(num_images):
        progress_percent += progress_per_file
        progress_label = "Registering "+str(imNum)+" of "+str(num_images)
        report_progress(progress_label,progress_percent)
    
        if moving_image_filenames[imNum] != fixed_image_filename:
            moving_im = itk.imread(moving_image_filenames[imNum],itk.F)
    
            imreg = tube.RegisterImages[ImageType].New()
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
            if output_dirname!=None:
                pname,fname = os.path.split(moving_image_filenames[imNum])
                rename_file_fname = os.path.splitext(fname)
                new_fname = str(rename_file_fname[0])+"_reg.nii"
                new_filename = os.path.join(output_dirname,new_fname)
                itk.imwrite(moving_reg_im,new_filename,compression=True)
        elif output_dirname!=None:
            pname,fname = os.path.split(moving_image_filenames[imNum])
            rename_file_fname = os.path.splitext(fname)
            new_fname = str(rename_file_fname[0])+"_reg.nii"
            new_filename = os.path.join(output_dirname,new_fname)
            itk.imwrite(moving_reg_im,new_filename,compression=True)
    report_progress("Done",100)

#################
#################
#################
#################
#################
def scv_register_atlas_to_image(atlas_im, atlas_mask_im, in_im):
    ImageType = itk.Image[itk.F,3]

    regAtlasToIn = tube.RegisterImages[ImageType].New(FixedImage=in_im,
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

#################
#################
#################
#################
#################
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
    time_max = float(time_arr.max())
    time_min = float(time_arr.min())
    nbins = int(number_of_time_bins)
    time_factor = (time_max-time_min)/(nbins+1)
    print("Time range =",time_min,"-",time_max)

    bin_value = np.zeros([num_regions,nbins])
    bin_count = np.zeros([num_regions,nbins])

    for atlas_region in range(num_regions):
        report_progress("Masking",(atlas_region+1)*(100/num_regions))
        indx_arr = np.where(atlas_arr==atlas_region)
        indx_list = list(zip(indx_arr[0],indx_arr[1],indx_arr[2]))
        for indx in indx_list:
            time_bin = int((time_arr[indx]-time_min)/time_factor)
            time_bin = min(max(0,time_bin),nbins-1)
            if np.isnan(vess_arr[indx]) == False:
                bin_count[atlas_region,time_bin] += 1
                bin_value[atlas_region,time_bin] += vess_arr[indx]

    bin_label = np.arange(nbins) * time_factor - time_min
    bin_value = np.divide(bin_value,bin_count,where=bin_count!=0)

    report_progress("Done",100)
    return bin_label,bin_value,bin_count

#################
#################
#################
#################
#################
def scv_convert_3d_files_to_4d_file(in_filenames,out_filename):
    num_3d_files = len(in_filenames)

    ImageType = itk.Image[itk.F, 3]
    Write4D = tube.Write4DImageFrom3DImages[ImageType].New()
    Write4D.SetNumberOfInputImages(num_3d_files)
    Write4D.SetFileName(out_filename)
    for i,file in enumerate(in_filenames):
        img = itk.imread(file,itk.F)
        Write4D.SetNthInputImage(i, img)
    Write4D.Update()

#################
#################
#################
#################
#################
def scv_prepare_3d_for_perfusion_toolbox(prep_3d_in_filenames,
                                         prep_3d_out_dirname,
                                         report_progress=print,
                                         report_subprogress=print,
                                         debug=False):
    num_3d_files = len(prep_3d_in_filenames)

    reg_fixed_image = prep_3d_in_filenames[num_3d_files//2]
    reg_in_filenames = prep_3d_in_filenames
    report_progress("Registering CTP",40)
    scv_register_ctp_images(reg_fixed_image,
        reg_in_filenames,
        output_dirname=prep_3d_out_dirname,
        report_progress=report_subprogress,
        debug=debug)

    # update filenames to registered ctp
    report_progress("Saving 4D CTP",60)
    new_ctp_3d_filenames = []
    for i in range(num_3d_files):
        rename_file_name = str(prep_3d_in_filenames[i])
        rename_file_name = os.path.splitext(rename_file_name)
        new_ctp_3d_filenames.append( os.path.realpath(os.path.join(
            prep_3d_out_dirname, str(rename_file_name[0]) + "_reg.nii")))

    # Write 4D ctp registered
    pname,fname = os.path.split(prep_3d_in_filenames[0])
    ppname,dirname = os.path.split(pname)
    ctp_base_filename = str(dirname) + "-4D_reg"
    ctp_filename = ctp_base_filename + ".nii"
    ctp_4d_out_filename = os.path.realpath(os.path.join(
        prep_3d_out_dirname, ctp_filename))
    scv_convert_3d_files_to_4d_file(new_ctp_3d_filenames,
        ctp_4d_out_filename)
    
    # Compute CT, CTA, DSA
    report_progress("Computing CT, CTA, DSA",70)
    ct_im,cta_im,dsa_im = scv_convert_ctp_to_cta(new_ctp_3d_filenames,
        report_progress = report_subprogress,
        debug=debug,
        output_dirname=prep_3d_out_dirname)
    ct_filename = ctp_base_filename + "_ct.nii"
    ct_out_filename = os.path.realpath(os.path.join(
        prep_3d_out_dirname, ct_filename))
    itk.imwrite(ct_im, ct_out_filename,compression=True)
    cta_filename = ctp_base_filename + "_cta.nii"
    cta_out_filename = os.path.realpath(os.path.join(
        prep_3d_out_dirname, cta_filename))
    itk.imwrite(cta_im, cta_out_filename,compression=True)
    dsa_filename = ctp_base_filename + "_dsa.nii"
    dsa_out_filename = os.path.realpath(os.path.join(
        prep_3d_out_dirname, dsa_filename))
    itk.imwrite(dsa_im, dsa_out_filename,compression=True)

    # Segment brain from CT
    report_progress("Segmenting Brain",80)
    ct_brain,mask_brain = scv_segment_brain_from_ct(ct_im,
        report_progress = report_subprogress,
        debug=debug)
    rename_file_ct = str(ct_filename)
    rename_file_ct = os.path.splitext(rename_file_ct)
    mask_brain_filename = str(rename_file_ct[0]) + "_brain_mask.nii"
    mask_brain_out_filename = os.path.realpath(os.path.join(
        prep_3d_out_dirname, mask_brain_filename))
    itk.imwrite(mask_brain, mask_brain_out_filename)

    report_progress("Done",100)

    return ctp_4d_out_filename, ct_out_filename, \
        cta_out_filename, dsa_out_filename, \
        mask_brain_out_filename

#################
#################
#################
#################
#################
def scv_prepare_4d_for_perfusion_toolbox(prep_4d_in_filename,
                                         prep_4d_out_dirname,
                                         report_progress=print,
                                         report_subprogress=print,
                                         debug=False):
    # convert 4D ctp to 3D images
    ctp_dirname,ctp_filename = os.path.split(prep_4d_in_filename)

    rename_file_ctp = os.path.splitext(str(ctp_filename))

    report_progress("Reading image",10)

    img4d_im = itk.imread(prep_4d_in_filename, itk.F)
    img4d_array = itk.GetArrayFromImage(img4d_im)
    img4d_shape = img4d_array.shape
    img4d_spacing = np.array(img4d_im.GetSpacing())
    img4d_direction = np.array(img4d_im.GetDirection())
    img4d_origin = np.array(img4d_im.GetOrigin())
    img3d_spacing = img4d_spacing[0:3]
    img3d_origin = img4d_origin[0:3]
    img3d_direction = img4d_direction[0:3, 0:3]
    num_3d_files = img4d_shape[0]
    new_filenames = [] 
    report_progress("Creating CTP",15)
    subprogress = 15
    subprogress_per_file = 100 / num_3d_files
    for i in range(num_3d_files):
        report_subprogress("Writing",
            subprogress+subprogress_per_file*i)
        tmp_filename = f'CTP_{i:03}.mha'
        new_filename = os.path.join(prep_4d_out_dirname,tmp_filename)
        img3d_array = img4d_im[i,:,:,:]
        img3d_im = itk.GetImageFromArray(img3d_array)
        img3d_im.SetSpacing(img3d_spacing)
        img3d_im.SetOrigin(img3d_origin)
        img3d_im.SetDirection(img3d_direction)
        itk.imwrite(img3d_im,new_filename,compression=True)
        new_filenames.append(new_filename)

    results = [new_filenames]
    results += scv_prepare_3d_for_perfusion_toolbox( new_filenames, \
        prep_4d_out_dirname, report_progress, report_subprogress, debug)

    return results

#################
#################
#################
#################
#################
def scv_fix_image_info(filename, match_image):
    im = itk.imread(filename,itk.F)
    im.SetSpacing(match_image.GetSpacing())
    im.SetOrigin(match_image.GetOrigin())
    im.SetDirection(match_image.GetDirection())
    itk.imwrite(im,filename,compression=True) 
    
#################
#################
#################
#################
#################
#matlab -r "addpath('./perfusion_toolbox');DSC_report('/data/UNC-Stroke/UNC/CTP/CTAT-001-PTO/CTAT-001-Perf-4D_reg.nii','/data/UNC-Stroke/UNC/CTP/CTAT-001-PTO/CTAT-001-Perf-4D_reg_ct_brain_mask.nii','./test');quit"
def scv_run_perfusion_toolbox(ctp_4d_in_filename,
                              ctp_mask_filename,
                              perfusion_out_dirname):
    cmd = "addpath('"+scv_get_perfusion_toolbox_path()+"');DSC_report('"+ \
          ctp_4d_in_filename+"','"+ctp_mask_filename+"','"+ \
          perfusion_out_dirname+"');quit"
    subprocess.run(["matlab", "-wait", "-r", cmd])

    mask_image = itk.imread(ctp_mask_filename,itk.F)
    cbf_filename = os.path.join(perfusion_out_dirname,"CBF_SVD.nii")
    scv_fix_image_info(cbf_filename,mask_image)

    cbv_filename = os.path.join(perfusion_out_dirname, "CBV.nii")
    scv_fix_image_info(cbv_filename,mask_image)

    cbv_lc_filename = os.path.join(perfusion_out_dirname, "CBV_LC.nii")
    scv_fix_image_info(cbv_lc_filename,mask_image)

    mtt_filename = os.path.join(perfusion_out_dirname, "MTT_SVD.nii")
    scv_fix_image_info(mtt_filename,mask_image)

    tmax_filename = os.path.join(perfusion_out_dirname, "Tmax_SVD.nii")
    scv_fix_image_info(tmax_filename,mask_image)

    ttp_filename = os.path.join(perfusion_out_dirname, "TTP.nii")
    scv_fix_image_info(ttp_filename,mask_image)
    
    return cbf_filename,cbv_filename,mtt_filename,tmax_filename,ttp_filename

 
#################
#################
#################
#################
#################
def scv_generate_vessel_report(ctp_3d_filenames,
                               ctp_4d_filename,
                               ct_filename,
                               cta_fielname,
                               dsa_filename,
                               mask_brain_filename,
                               atlas_path,
                               report_out_dirname,
                               report_progress=print,
                               report_subprogress=print,
                               debug=False):
    new_ctp_filenames = []
    base_3d_image = itk.imread(ctp_3d_filenames[0], itk.F)
    ImageMath = tube.ImageMath.New(base_3d_image)
    for filename in ctp_3d_filenames:
        img = itk.imread(filename, itk.F)
        ImageMath.SetInput(img)
        ImageMath.Blur(0.5)
        ImageMath.BlurOrder(2.0,0,2)
        new_img = ImageMath.GetOutput()
        Resample = tube.ResampleImage.New(Input=new_img)
        Resample.SetSpacing([1.5,1.5,5])
        Resample.SetInterpolator("Sinc")
        Resample.Update()
        img = Resample.GetOutput()
        org_filename = os.path.splitext(filename)
        new_filename = str(org_filename[0])+'_15x15x5.nii'
        itk.imwrite(img,new_filename,compression=True)
        new_ctp_filenames.append(new_filename)
    
    org_filename = os.path.splitext(ctp_4d_filename)
    new_ctp_4d_filename = str(org_filename[0])+'_15x15x5.nii'
    scv_convert_3d_files_to_4d_file(new_ctp_filenames,
        new_ctp_4d_filename)

    match_image = itk.imread(new_ctp_filenames[0], itk.UC)
    mask = itk.imread(mask_brain_filename,itk.UC)
    ResampleMask = tube.ResampleImage.New(Input=mask)
    ResampleMask.SetMatchImage(match_image)
    ResampleMask.SetInterpolator("NearestNeighbor")
    ResampleMask.Update()
    new_mask = ResampleMask.GetOutput()
    org_filename = os.path.splitext(mask_brain_filename)
    new_mask_filename = str(org_filename[0])+'_15x15x5.nii'
    itk.imwrite(new_mask,new_mask_filename,compression=True)

    # Call matlab and pass it the 4D ctp filename and the output directory
    cbf_filename,cbv_filename,mtt_filename,tmax_filename,ttp_filename = \
        scv_run_perfusion_toolbox(new_ctp_4d_filename, \
            new_mask_filename, report_out_dirname)

    # Vessel enhancement and extraction
    in_im = itk.imread(dsa_filename, itk.F)

    in_filename_base = str(os.path.splitext(dsa_filename)[0])

    brain_mask_im = itk.imread(mask_brain_filename, itk.F)
    ImageMath.SetInput(in_im)
    ImageMath.ReplaceValuesOutsideMaskRange(brain_mask_im,0.9,1.1,0)
    in_brain_im = ImageMath.GetOutput()

    report_progress("Enhancing vessels",40)
    # Enhancing vessels creates an image in which intensity is
    #    related to "vesselness" instead of being related to the
    #    amount of contrast agent in the vessel.  This simplifies
    #    subsequent vessel seeding and traversal stopping criteria.
    in_vess_im,in_brain_vess_im = scv_enhance_vessels_in_cta(
        in_im,
        in_brain_im,
        report_progress=report_subprogress,
        debug=debug)
    itk.imwrite(in_vess_im,
        os.path.join(report_out_dirname,
            in_filename_base+"_vessels_enhanced.mha"),
        compression=True)
    itk.imwrite(in_brain_vess_im,
        os.path.join(report_out_dirname,
            in_filename_base+"_brain_vessels_enhanced.mha"),
        compression=True)

    report_progress("Extracting vessels",60)
    vess_mask_im,vess_so = scv_extract_vessels_from_cta(
        in_vess_im,
        in_brain_vess_im,
        report_progress=report_subprogress,
        debug=debug,
        output_dirname=report_out_dirname)

    itk.imwrite(in_brain_vess_im,
        os.path.join(report_out_dirname,
            in_filename_base+"_vessels_extracted.mha"),
        compression=True)

    SOWriter = itk.SpatialObjectWriter[3].New()
    SOWriter.SetInput(vess_so)
    SOWriter.SetBinaryPoints(True)
    SOWriter.SetFileName(os.path.join(report_out_dirname,
        in_filename_base+"_vessels_extracted.tre"))
    SOWriter.Update()

    VTPWriter = itk.WriteTubesAsPolyData.New()
    VTPWriter.SetInput(vess_so)
    VTPWriter.SetFileName(os.path.join(report_out_dirname,
        in_filename_base+"_vessels_extracted.vtp"))
    VTPWriter.Update()
 
    report_progress("Generating Perfusion Stats",80)

    script_dirname = os.path.dirname(os.path.realpath(__file__))
    atlas_im = itk.imread(
        os.path.join(atlas_path,'atlas_brainweb.mha'), itk.F)
    atlas_mask_im = itk.imread(
        os.path.join(atlas_path,'atlas_brainweb_mask.mha'), itk.F)
    atlas_reg_im,atlas_mask_reg_im = scv_register_atlas_to_image(
        atlas_im,
        atlas_mask_im,
        in_brain_im)
    ImageMath = tube.ImageMath.New(Input=atlas_mask_reg_im)
    ImageMath.ReplaceValuesOutsideMaskRange(vess_mask_im,
        0.000001,9999,4)
    ImageMath.ReplaceValuesOutsideMaskRange(in_brain_im,
        0.000001,9999,0)
    vess_atlas_mask_im = ImageMath.GetOutput()
    itk.imwrite(vess_atlas_mask_im,
        os.path.join(report_out_dirname,
            in_filename_base+"_vessels_atlas_mask.mha"),
        compression=True)

    TubeMath = tube.TubeMath[3,itk.F].New()
    TubeMath.SetInputTubeGroup(vess_so)
    TubeMath.SetUseAllTubes()
    TubeMath.ComputeTubeRegions(vess_atlas_mask_im)
    
    graph_label = None
    graph_data = None
    ttp_im = None
    if len(ttp_filename) > 0:
        report_progress("Generating TTP Graphs",92)
        ttp_im = itk.imread(ttp_filename, itk.F)
        Resample = tube.ResampleImage.New(Input=ttp_im)
        Resample.SetMatchImage(vess_atlas_mask_im)
        Resample.Update()
        fit_ttp_im = Resample.GetOutput()
        TubeMath.SetPointValuesFromImage(fit_ttp_im, "TTP")
        TubeMath.SetPointValuesFromTubeRegions(fit_ttp_im,
            "TTP_Tissue",
            1.5,
            4)
        TubeMath.SmoothTubeProperty("TTP",4)
        TubeMath.SmoothTubeProperty("TTP_Tissue",12)
        time_bin,ttp_bin,ttp_count = scv_compute_atlas_region_stats(
            vess_atlas_mask_im,
            fit_ttp_im,
            fit_ttp_im,
            100,
            report_subprogress)
        graph_label = ["Bin_Num"]
        graph_data = np.arange(len(time_bin))
        graph_label = np.append(graph_label,"TPP")
        graph_data = np.stack((graph_data,time_bin))
        for r in range(1,ttp_bin.shape[0]):
            graph_label = np.append(graph_label,
                "Count_Region_"+str(r))
            graph_data = np.concatenate((graph_data,
                [ttp_count[r,:]]))

    if len(cbf_filename) > 0:
        report_progress("Generating CBF Graphs",94)
        cbf_im = itk.imread(cbf_filename, itk.F)
        Resample = tube.ResampleImage.New(Input=cbf_im)
        Resample.SetMatchImage(vess_atlas_mask_im)
        Resample.Update()
        fit_cbf_im = Resample.GetOutput()
        TubeMath.SetPointValuesFromImage(fit_cbf_im, "CBF")
        TubeMath.SetPointValuesFromTubeRegions(fit_cbf_im,
            "CBF_Tissue",
            1.5,
            4)
        TubeMath.SmoothTubeProperty("CBF",4)
        TubeMath.SmoothTubeProperty("CBF_Tissue",12)
        if ttp_im!=None:
            time_bin,cbf_bin,cbf_count = scv_compute_atlas_region_stats(
                vess_atlas_mask_im,
                fit_ttp_im,
                fit_cbf_im,
                100,
                report_subprogress)
            for r in range(1,cbf_bin.shape[0]):
                graph_label = np.append(graph_label,
                    "CBF_Region"+str(r))
                graph_data = np.concatenate((graph_data,
                    [cbf_bin[r,:]]))

    if len(cbv_filename) > 0:
        report_progress("Generating CBV Graphs",96)
        cbv_im = itk.imread(cbv_filename, itk.F)
        Resample = tube.ResampleImage.New(Input=cbv_im)
        Resample.SetMatchImage(vess_atlas_mask_im)
        Resample.Update()
        fit_cbv_im = Resample.GetOutput()
        TubeMath.SetPointValuesFromImage(fit_cbv_im, "CBV")
        TubeMath.SetPointValuesFromTubeRegions(fit_cbv_im,
            "CBV_Tissue",
            1.5,
            4)
        TubeMath.SmoothTubeProperty("CBV",4)
        TubeMath.SmoothTubeProperty("CBV_Tissue",12)
        if ttp_im!=None:
            time_bin,cbv_bin,cbv_count = scv_compute_atlas_region_stats(
                vess_atlas_mask_im,
                fit_ttp_im,
                fit_cbv_im,
                100,
                report_subprogress)
            for r in range(1,cbv_bin.shape[0]):
                graph_label = np.append(graph_label,
                    "CBV_Region"+str(r))
                graph_data = np.concatenate((graph_data,
                    [cbv_bin[r,:]]))
    if len(tmax_filename) > 0:
        report_progress("Generating TMax Graphs",98)
        tmax_im = itk.imread(tmax_filename, itk.F)
        Resample = tube.ResampleImage.New(Input=tmax_im)
        Resample.SetMatchImage(vess_atlas_mask_im)
        Resample.Update()
        fit_tmax_im = Resample.GetOutput()
        TubeMath.SetPointValuesFromImage(fit_tmax_im, "TMax")
        TubeMath.SetPointValuesFromTubeRegions(fit_tmax_im,
            "TMax_Tissue",
            1.5,
            4)
        TubeMath.SmoothTubeProperty("TMax",4)
        TubeMath.SmoothTubeProperty("TMax_Tissue",12)
        if ttp_im!=None:
            time_bin,tmax_bin,tmax_count = scv_compute_atlas_region_stats(
                vess_atlas_mask_im,
                fit_ttp_im,
                fit_tmax_im,
                100,
                report_subprogress)
            for r in range(1,tmax_bin.shape[0]):
                graph_label = np.append(graph_label,
                    "TMax_Region"+str(r))
                graph_data = np.concatenate((graph_data,
                    [tmax_bin[r,:]]))

    report_progress("Saving results",99)
    SOWriter = itk.SpatialObjectWriter[3].New()
    SOWriter.SetInput(vess_so)
    SOWriter.SetBinaryPoints(True)
    SOWriter.SetFileName(os.path.join(report_out_dirname,
        in_filename_base+"_vessels_extracted_perf.tre"))
    SOWriter.Update()

    VTPWriter = itk.WriteTubesAsPolyData.New()
    VTPWriter.SetInput(vess_so)
    VTPWriter.SetFileName(os.path.join(report_out_dirname,
        in_filename_base+"_vessels_extracted_perf.vtp"))
    VTPWriter.Update()

    csvfilename = os.path.join(report_out_dirname,
        in_filename_base+"_vessels_extracted_perf.csv")
    csvfile = open(csvfilename,'w',newline='')
    csvwriter = csv.writer(csvfile, dialect='excel',
        quoting=csv.QUOTE_NONE)
    csvwriter.writerow(graph_label)
    for r in range(graph_data.shape[1]):
        csvwriter.writerow(['{:f}'.format(x) for x in graph_data[:,r]])
    csvfile.close()
    report_progress("Done",100)


#################
#################
#################
#################
#################
def scv_generate_4d_ctp_vessel_report(ctp_4d_filename,
                                      atlas_path,
                                      report_out_dirname,
                                      report_progress=print,
                                      report_subprogress=print,
                                      debug=False):

    ctp_3d_filenames,ctp_4d_filename,ct_filename, \
        cta_filename,dsa_filename,mask_brain_filename \
            = scv_prepare_4d_for_perfusion_toolbox( \
                ctp_4d_filename, report_out_dirname, \
                report_progress, report_subprogress, debug)


    scv_generate_vessel_report(ctp_3d_filenames, \
        ctp_4d_filename,ct_filename, \
        cta_filename,dsa_filename, \
        mask_brain_filename,atlas_path,report_out_dirname, \
        report_progress,report_subprogress,debug)


#################
#################
#################
#################
#################
def scv_generate_3d_ctp_vessel_report(ctp_3d_filenames,
                                      atlas_path,
                                      report_out_dirname,
                                      report_progress=print,
                                      report_subprogress=print,
                                      debug=False):
    ctp_3d_filenames,ctp_4d_filename,ct_filename, \
        cta_filename,dsa_filename,mask_brain_filename \
            = scv_prepare_3d_for_perfusion_toolbox( \
                ctp_3d_filename, report_out_dirname, \
                report_progress, report_subprogress, debug)

    scv_generate_vessel_report(ctp_3d_filenames, \
        ctp_4d_filename,ct_filename, \
        cta_filename,dsa_filename, \
        mask_brain_filename,atlas_path,report_out_dirname, \
        report_progress,report_subprogress,debug)

