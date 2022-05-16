% DSC_mri_toolbox demo

% ------ Load the dataset to be analyzed ---------------------------------

%main_dir = '/Users/peirong/Downloads/training_14';
%main_dir = '/Users/peirong/Downloads/CTP_Stephen/002-reg';
main_dir = '/Data/UNC-Stroke/UNC/CTP/CTAT-001-PTO/';


% CTAT-001
savepath = fullfile(main_dir, 'PerfusionMaps_5mm_b5_s2');
mkdir(savepath)
%mrp_movie = fullfile(main_dir, 'VSD.Brain.XX.O.MR_4DPWI.127055/VSD.Brain.XX.O.MR_4DPWI.127055.nii');
ctp_movie = fullfile(main_dir, 'CTAT-001-Perf-4D_reg5_b5_s2.nii');
% demo
%savepath = '/Users/peirong/Documents/MATLAB/Perfusion Toolbox/demo-data';
%test_volume   = niftiread(fullfile(savepath,'GRE_DSC.nii'));

% ---------------------- %
% -------- TODO -------- %
% ---------------------- %
%test_volume = niftiread(mrp_movie);
test_volume = niftiread(ctp_movie);
% ---------------------- %
% ---------------------- %
% ---------------------- %




% ------ For our MRP data (Useless when computing demo MRP) ------ % 
R = length(test_volume(:,1,1,1,1));
V = length(test_volume(1,:,1,1,1));
S = length(test_volume(1,1,:,1,1));
T = length(test_volume(1,1,1,:,1));
test_volume = reshape(test_volume, [R, V, S, T]);

% ------ Set minimum acquistion parameters -------------------------------
TE = 0.025; % 25ms
TR = 1.55;  % 1.55s

% ------ Perform quantification ------------------------------------------ 
% Input   test_volume (4D matrix with raw GRE-DSC acquisition)
%         TE         (Echo time)
%         TR         (Repetition time)
% Output  cbv        (3D matrix with standard rCBV values)
%         cbf        (struct with 3D matrices of rCBF values for each method selected)
%         mtt        (struct with 3D matrices of MTT values for each method selected)
%         cbv_lc     (3D matrix with leackage corrected rCBV values)
%         ttp        (3D matrix with leackage corrected Time to Peak values)
%         mask       (3D matrix with computed mask)
%         aif        (struct with AIF extracted with clustering algorithm)
%         conc       (4D matrix with pseudo-concentration values)
%         s0         (3D matrix with S0 estimates from pre-contrast images)

[cbv,cbf,mtt,cbv_lc,ttp,tmax,mask,aif,conc,s0]=DSC_mri_core(test_volume,TE,TR);
res_svd = cbf.svd.residual;
cbf_svd = cbf.svd.map;
%cbf_csvd = cbf.csvd.map;
%cbf_osvd = cbf.osvd.map;
tmax_svd = tmax.svd;
%tmax_csvd = tmax.csvd;
%tmax_osvd = tmax.osvd;
mtt_svd = mtt.svd;
%mtt_csvd = mtt.csvd;
%mtt_osvd = mtt.osvd;
conc_gv = conc;
aif_gv_params = aif.fit.parameters;
% ------  Save Results --------------------------------------------------- 
niftiwrite(res_svd,fullfile(savepath,'res_svd.nii'));
niftiwrite(cbv,fullfile(savepath,'CBV.nii'));
niftiwrite(cbv_lc,fullfile(savepath,'CBV_LC.nii'));
niftiwrite(cbf_svd,fullfile(savepath,'CBF_SVD.nii'));
%niftiwrite(cbf_csvd,fullfile(savepath,'CBF_CSVD.nii'));
%niftiwrite(cbf_osvd,fullfile(savepath,'CBF_OSVD.nii'));
niftiwrite(tmax_svd,fullfile(savepath,'Tmax_SVD.nii'));
%niftiwrite(tmax_csvd,fullfile(savepath,'Tmax_CSVD.nii'));
%niftiwrite(tmax_osvd,fullfile(savepath,'Tmax_OSVD.nii'));
niftiwrite(mtt_svd,fullfile(savepath,'MTT_SVD.nii'));
%niftiwrite(mtt_csvd,fullfile(savepath,'MTT_CSVD.nii'));
%niftiwrite(mtt_osvd,fullfile(savepath,'MTT_OSVD.nii'));
niftiwrite(ttp,fullfile(savepath,'TTP.nii'));
niftiwrite(double(mask),fullfile(savepath,'Mask.nii'));
%niftiwrite(conc_gv,fullfile(savepath,'CTC_GV.nii'));
%fit_file = fopen(fullfile(savepath, 'AIF_GV_Fit.txt'), 'wt');
%fprintf(fit_file, 'FP(t)= A*((t-t0)^alpha)*exp(-(t-t0)/beta)\n');
%fprintf(fit_file, 'ricircolo(t)= FP(t-td) conv K*exp(-t/tao)\n');
%fprintf(fit_file, 'GV Fitted parameters:\nt0: %f\n', aif_gv_params(1));
%fprintf(fit_file, 'alpha: %f\n', aif_gv_params(2));
%fprintf(fit_file, 'beta: %f\n', aif_gv_params(3));
%fprintf(fit_file, 'A: %f\n', aif_gv_params(4));
%fprintf(fit_file, 'td: %f\n', aif_gv_params(5));
%fprintf(fit_file, 'K: %f\n', aif_gv_params(6));
%fprintf(fit_file, 'tao: %f\n', aif_gv_params(7));

% ------  View Results --------------------------------------------------- 
%DSC_mri_show_results(cbv_lc,cbf,mtt,ttp,mask,aif,conc,s0);