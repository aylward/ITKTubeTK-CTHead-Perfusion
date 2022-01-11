#!/usr/bin/env python
# coding: utf-8

import itk
from itk import TubeTK as ttk

import numpy as np

def scv_segment_brain_from_CTA( cta_image ):
    ImageType = itk.Image[itk.F, 3]
    LabelMapType = itk.Image[itk.UC,3]

    thresh = ttk.ImageMath.New(Input=cta_image)
    thresh.ReplaceValuesOutsideMaskRange(cta_image,1,6000,0)
    thresh.ReplaceValuesOutsideMaskRange(cta_image,0,600,1)
    cta_tmp = thresh.GetOutput()
    thresh.ReplaceValuesOutsideMaskRange(cta_tmp,0,1,2)
    cta_mask = thresh.GetOutputUChar()

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

    maskMath.SetInput(brainMaskRaw)
    maskMath.Threshold(2,2,1,0)
    maskMath.Erode(1,1,0)
    brainMaskRaw2 = maskMath.GetOutputUChar()

    connComp = ttk.SegmentConnectedComponents.New(Input=brainMaskRaw2)
    connComp.SetKeepOnlyLargestComponent(True)
    connComp.Update()
    brainMask = connComp.GetOutput()

    cast = itk.CastImageFilter[LabelMapType, ImageType].New()
    cast.SetInput(brainMask)
    cast.Update()
    brainMaskF = cast.GetOutput()

    brainMath = ttk.ImageMath[ImageType,ImageType].New(Input=cta_image)
    brainMath.ReplaceValuesOutsideMaskRange( brainMaskF, 1, 1, 0)
    cta_brain_image = brainMath.GetOutput()

    return cta_brain_image

def scv_enhance_vessels_in_brain_cta( cta_image, cta_brain_image ):
    ImageType = itk.Image[itk.F, 3]
    LabelMapType = itk.Image[itk.UC,3]

    imMath = ttk.ImageMath.New(Input=cta_brain_image)
    imMath.Threshold( 0.00001, 4000, 1, 0)
    imMath.Erode(10,1,0)
    imBrainMaskErode = imMath.GetOutput()
    imMath.SetInput(cta_brain_image)
    imMath.IntensityWindow(0,300,0,300)
    imMath.ReplaceValuesOutsideMaskRange(imBrainMaskErode,0.5,1.5,0)
    imBrainErode = imMath.GetOutput()

    imMath = ttk.ImageMath[ImageType,ImageType].New()
    imMath.SetInput(imBrainErode)
    imMath.Blur(1.5)
    imBlur = imMath.GetOutput()
    imBlurArray = itk.GetArrayViewFromImage(imBlur)

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
        seedCoord[:][i] = cta_brain_image.TransformIndexToPhysicalPoint(indx)

    vSeg = ttk.SegmentTubes.New(Input=cta_brain_image)
    vSeg.SetVerbose(True)
    vSeg.SetMinRoundness(0.4)
    vSeg.SetMinCurvature(0.002)
    vSeg.SetRadiusInObjectSpace( 1 )
    for i in range(numSeeds):
        vSeg.ExtractTubeInObjectSpace( seedCoord[i], i )
    tubeMaskImage = vSeg.GetTubeMaskImage()

    imMath.SetInput(tubeMaskImage)
    imMath.AddImages(cta_brain_image, 200, 1)
    blendIm = imMath.GetOutput()

    trMask = ttk.ComputeTrainingMask[ImageType,LabelMapType].New()
    trMask.SetInput( tubeMaskImage )
    trMask.SetGap( 4 )
    trMask.SetObjectWidth( 1 )
    trMask.SetNotObjectWidth( 1 )
    trMask.Update()
    fgMask = trMask.GetOutput()

    enhancer = ttk.EnhanceTubesUsingDiscriminantAnalysis[ImageType,
                   LabelMapType].New()
    enhancer.AddInput( cta_image )
    enhancer.SetLabelMap( fgMask )
    enhancer.SetRidgeId( 255 )
    enhancer.SetBackgroundId( 128 )
    enhancer.SetUnknownId( 0 )
    enhancer.SetTrainClassifier(True)
    enhancer.SetUseIntensityOnly(True)
    enhancer.SetScales([0.43,1.29,3.01])
    enhancer.Update()
    enhancer.ClassifyImages()

    cta_vess = itk.SubtractImageFilter(
                  Input1=enhancer.GetClassProbabilityImage(0),
                  Input2=enhancer.GetClassProbabilityImage(1))

    imMath.SetInput(cta_brain_image)
    imMath.Threshold(0.0001,2000,1,0)
    imMath.Erode(2,1,0)
    imBrainE = imMath.GetOutput()

    imMath.SetInput(cta_vess)
    imMath.ReplaceValuesOutsideMaskRange(imBrainE, 1, 1, -0.001)
    cta_brain_vess = imMath.GetOutput()

    return cta_vess, cta_brain_vess
