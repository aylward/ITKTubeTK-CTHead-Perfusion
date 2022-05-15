% DSC_mri_toolbox demo

% ------ Load the dataset to be analyzed ---------------------------------
%datapath = '/Users/peirong/Documents/MATLAB/Perfusion Toolbox/demo-data';
%DSC_info   = niftiinfo(fullfile(datapath,'GRE_DSC.nii'));

datapath = '/Users/peirong/Downloads/stroke/tr1';
DSC_info   = niftiinfo(fullfile(datapath,'tr-1-VSD.Brain.XX.O.MR_4DPWI.127015.nii'));

%datapath = '/Users/peirong/Downloads/stroke/tr4';
%DSC_info   = niftiinfo(fullfile(datapath,'tr-4-CTC_Axial.nii'));

%datapath = '/Users/peirong/Downloads/stroke/tr8';
%CTC_info   = niftiinfo(fullfile(datapath,'tr-8-CTC_Axial.nii'));


volumes = niftiread(DSC_info);

% Only for ISLES data
R = length(volumes(:,1,1,1,1));V = length(volumes(1,:,1,1,1));S = length(volumes(1,1,:,1,1));T = length(volumes(1,1,1,1,:));volumes = reshape(volumes, [R, V, S, T]);

% ------ Set minimum acquistion parameters -------------------------------
TE = 0.025; % 25ms
TR = 1.55;  % 1.55s
options=DSC_mri_getOptions;
volumes = double(volumes);
[nR,nC,nS,nT]=size(volumes);
options.nR=nR;
options.nC=nC;
options.nS=nS;
options.nT=nT;
options.te=TE;
options.tr=TR;
options.time=0:TR:(nT-1)*TR;

[mask]=DSC_mri_mask(volumes,options);
[conc,s0,bolus]=DSC_mri_conc(volumes,mask.data,options);
niftiwrite(conc,fullfile(datapath,'conc.nii'));
[fit_ctc, params] = gv_fit_core(conc, options);

niftiwrite(fit_ctc,fullfile(datapath,'fit_ctc.nii'));
niftiwrite(params.t0,fullfile(datapath,'t0.nii'));
niftiwrite(params.alpha,fullfile(datapath,'alpha.nii'));
niftiwrite(params.beta,fullfile(datapath,'beta.nii'));
niftiwrite(params.A,fullfile(datapath,'A.nii'));