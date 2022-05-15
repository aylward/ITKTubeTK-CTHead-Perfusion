function [cbv,cbf,mtt,cbv_lc,ttp,tmax,mask,aif,conc,s0,fwhm,K2_map]=DSC_mri_core(volumes,te,tr,mask,optionsIN,aif)
% last modification: Marco Castellaro 26/05/2018

script_path = which(mfilename); % mfilename('fullpath');
[filepath,filename,fileext] = fileparts(script_path);
addpath(fullfile(filepath,"utils"));

%----- CHECK OF INPUT PARAMETERS - PART 1 ----------------------
% Check that input and output has the minimum number of mandatory parameters 
% Input
if nargin<4
    error('Input data required: volumes, te, tr, mask')
end

% Output
if nargout < 3
    error('Required almost three output parameters: cbf,cbv and mtt.')
end

% Check if options are provided, otherwise load default parameters
if nargin < 5
    % Load default options
    options=DSC_mri_getOptions;  
else
    % Use provided options
    options=optionsIN;
    clear optionsIN;
end

%----- INSERIMENTO DIMENSIONI VETT. OPZIONI ------------------------------
if options.display > 0
    disp('Checking data...');
end
volumes = double(volumes);
[nR,nC,nS,nT]=size(volumes);
options.nR=nR;
options.nC=nC;
options.nS=nS;
options.nT=nT;

%----- INSERIMENTO TEMPI NEL VETT. OPZIONI -------------------------------
options.te=te;
options.tr=tr;
options.time=0:tr:(nT-1)*tr;

if options.display > 0
    disp('                      DATA SIZE ');
    disp(['                     Rows - ' num2str(options.nR)]);
    disp(['                  Columns - ' num2str(options.nC)]);
    disp(['                   Slices - ' num2str(options.nS)]);
    disp(['                  Samples - ' num2str(options.nT)]);
    disp(['                Echo time - ' num2str(options.te) ' s']);
    disp(['          Repetition time - ' num2str(options.tr) ' s']);
end

if not(nR==size(mask,1))
        error('Rows mask not equal to data.')
    elseif not(nC==size(mask,2))
            error('Columns mask not equal to data.')
        elseif not(nS==size(mask,3))
                error('Slices mask not equal to data.')
            else
                if options.aif.enable
                    [mask]=DSC_mri_mask_only_aif(volumes,mask,options);
                else
                    temp=mask;
                    clear mask;
                    mask.data=temp;
end

%----- CHECK OF INPUT PARAMETERS - PART 2 ----------------------
% Check wether the AIF is column of row vector
if nargin > 5
    if not(isempty(aif))
        if not(nT==size(aif.conc,1))
            if not(nT==size(aif.conc,2))
                if size(aif.conc,1)==0 && size(aif.conc,2)==0
                    options.aif=1;
                else
                    error('AIF dimensions are not compatible to samples data, please provide a compatible AIF.')
                end
            end
        end
    end
end



%----- CALCOLO DELLE CONCENTRAZIONI E DI S0 ------------------------------
if options.conc
    conc=volumes;
    options.aif.nSlice=aif.sliceAIF;
    %----- CALCOLO SI s0 - OPZIONALE -----------------------------------------
elseif nargout > 7  % default
    [conc,s0,bolus]=DSC_mri_conc(volumes,mask.data,options);
    conc = real(conc);
else
    [conc,s0,bolus]=DSC_mri_conc(volumes,mask.data,options);
    conc = real(conc);
end

%----- ESTRAZIONE DELL'AIF -----------------------------------------------
if options.aif.enable
    [aif]=DSC_mri_aif(conc,mask.aif,options);
end


%----- MAP Calculation -----------------------------------------------
if options.display>0
    disp(' ')
    disp('Calculating maps...')
end

    
%----- CBV calculation ---------------------------------------------------
[cbv]=DSC_mri_cbv(conc,aif.fit.gv,mask,options);

%----- CBV leackage correction  ------------------------------------------
[cbv_lc,~,K2_map,~,~]=DSC_mri_cbv_lc(conc,aif.fit.gv,mask,bolus,options);

%----- CBF calculation ---------------------------------------------------
[cbf, tmax]=DSC_mri_cbf(conc,aif.fit.gv,mask,options);

%----- MTT calculation ---------------------------------------------------
[mtt]=DSC_mri_mtt(cbv_lc,cbf,mask,options);

%----- TTP calculation ---------------------------------------------------
if nargout > 3
    [ttp]=DSC_mri_ttp(conc,mask.data,options);
    [fwhm]=DSC_mri_fwhm(conc,mask.data,options);
end


%----- Output refinements -----------------------------------------
mask=mask.data;

end
