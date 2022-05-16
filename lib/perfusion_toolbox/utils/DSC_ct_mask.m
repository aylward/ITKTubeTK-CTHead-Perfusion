

function [mask, volume_mean]=DSC_ct_mask(volumes,options)
if options.display > 0
    disp(' ')
    disp('Masking CTP data... ');
end
volume_mean=mean(volumes,4);
%idx = volume_sum~=0;
volume_mean(volume_mean > 0.5 | volume_mean < - 0.5) = 1;
for slc = 1 : length(volume_mean(1, 1, :))
    volume_mean(:, :, slc) = imfill(volume_mean(:, :, slc));
end
mask.data = volume_mean;
mask.aif= mask.data;
end