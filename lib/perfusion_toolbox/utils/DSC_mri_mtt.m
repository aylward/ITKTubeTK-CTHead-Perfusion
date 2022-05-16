function [mtt]=DSC_mri_mtt(cbv,cbf,mask,options)
if options.display > 0
    disp('   MTT');
end

deconv_method= fieldnames(cbf);

for method=1:size(deconv_method,1)
    eval(['mtt.' deconv_method{method,:} '=cbv./cbf.'  deconv_method{method,:} '.map;']);
    mtt.svd = mtt.svd.* mask.data;
end