function [fit_ctc, param] = gv_fit_core(volumes, options)
volumes = double(volumes);
[nR, nC, nS, nT] = size(volumes);

fit_ctc = zeros(nR, nC, nS, nT);
param.t0 = zeros(nR, nC, nS);
param.alpha = zeros(nR, nC, nS);
param.beta = zeros(nR, nC, nS);
param.A = zeros(nR, nC, nS);


for r = 1:nR
    sprintf('%d', r)
    for c = 1:nC
        for s = 1:nS
            if mean(volumes(r, c, s, :)) ~= 0
                for t = 1:nT
                    conc(t) = volumes(r, c, s, t);
                end
                pesi = 0.01 + exp(-conc);
                [~, TTP] = max(conc);
                if TTP == 1
                    TTP = 2;
                end
                if TTP == nT
                    TTP = nT - 1;
                end
                pesi(TTP) = pesi(TTP - 1) ./ 5;
                pesi(TTP + 1) = pesi(TTP + 1) ./ 2;
                [fitParameters_picco1]=fitGV_picco1(conc, pesi, options);
                if options.aif.ricircolo
                    [fitParameters_picco2]=fitGV_picco2(AIFconc,pesi,fitParameters_picco1,options);
                    fitParameters=[fitParameters_picco1(1:4) fitParameters_picco2(1:3)]';
                else
                    fitParameters = fitParameters_picco1(1:4);
                    param.t0(r, c, s) = fitParameters(1);
                    param.alpha(r, c, s) = fitParameters(2);
                    param.beta(r, c, s) = fitParameters(3);
                    param.A(r, c, s) = fitParameters(4);
                end
                if options.aif.ricircolo
                    fit_ctc(r, c, s, :) = GVfunction(fitParameters, options);
                else
                    fit_ctc(r, c, s, :) = GVfunction_picco1(fitParameters, options);
                end
            end
        end
    end
end


%% ------------------------------------------------------------------------
function [GVparametri]   = fitGV_picco1(dati, pesi, options_DSC)
% Calcola il fit del primo picco con una funzione gamma-variata.
% La funzione usata � descritta dalla formula:
%
% FP(t)=A*((t-t0)^alpha)*exp(-(t-t0)/beta)
%
% c(t)=FP(t)
%
% parametri: p=[t0 alpha beta A]
%
% L'ultimo parametro restituito rappresenta l'exitflag, che pu� assumere i
% seguenti valori:
%      1  LSQNONLIN converged to a solution X.
%      2  Change in X smaller than the specified tolerance.
%      3  Change in the residual smaller than the specified tolerance.
%      4  Magnitude search direction smaller than the specified tolerance.
%      5  Voxel nullo
%      0  Maximum number of function evaluations or of iterations reached.
%     -1  Algorithm terminated by the output function.
%     -2  Bounds are inconsistent.
%     -4  Line search cannot sufficiently decrease the residual along the
%         current search direction.

% OPZIONI STIMATORE
options             = optimset('lsqnonlin') ;
options.Display     = 'none'                ;
options.MaxFunEvals = 1000                 ;
options.MaxIter     = 1000                 ;
options.TolX        = 1e-4 ;
options.TolFun      = 1e-4 ;
%options.TolCon      = 1e-2 ;
%options.TolPCG      = 1e-8 ;
options.LargeScale  = 'on' ;
%options.DiffMinChange = 1e-18;
%options.DiffMaxChange = 2  ;

% STIME INIZIALI DEI PARAMETRI (modifica di DENIS)
% Alpha viene impostato a 5
alpha_init=5;

% t0 viene stimato sui dati iniziali. E' calcolato come l'ultimo istante in
% cui i dati rimangono in modulo inferiori al 5% del picco.
[MCdati,TTPpos]=max(dati);
TTPdati=options_DSC.time(TTPpos);
t0_init=options_DSC.time(find(dati(1:TTPpos)<=0.05*MCdati, 1, 'last' ));
if isempty(t0_init)
    t0_init = 1;
end

% beta viene stimato sfruttando la relazione che TTP=t0+alpha*beta
beta_init=(TTPdati-t0_init)./alpha_init;

% Inizializzo i parametri [t0 alpha beta] e scelgo A in modo che la stima
% iniziale e i dati abbiano lo stesso massimo.
A_init= MCdati./max(GVfunction_picco1([t0_init; alpha_init; beta_init; 1],options_DSC));

% Valori iniziali dei parametri per la stima
% p  = [t0  alpha  beta  A]
p0   = [t0_init;   alpha_init;    beta_init;   A_init] ; % Valori iniziali
lb   = p0.*0.1; % Estremi inferiori
ub   = p0.*10 ; % Estremi superiori

if options_DSC.display>2
    h=figure();
    plot(options_DSC.time,dati,'ko',options_DSC.time,GVfunction_picco1(p0,options_DSC),'g-')
    title('First peak fit - initial values')
end

% Controllo i dati, devono essere vettori colonna
if size(options_DSC.time,1)==1
    % controlla che il vettore dei options.time sia un vettore colonna
    options_DSC.time=options_DSC.time';
end
if size(dati,1)==1
    % controlla che il vettore dei options.time sia un vettore colonna
    dati=dati';
end
if size(pesi,1)==1
    % controlla che il vettore dei options.time sia un vettore colonna
    pesi=pesi';
end

% MARCO
% AUMENTO LA PRECISIONE DEL PICCO
[~, TTP]=max(dati);
if TTP == 1
    TTP = 2;
end
pesi(TTP)=pesi(TTP)./10;
pesi(TTP-1)=pesi(TTP-1)./2;


%TROVO FINE PRIMO PICCO (20% valore massimo)
i=TTP;
while dati(i)>0.2*dati(TTP) && i < length(dati)
    i=i+1;
end

%ADATTO I DATI PER "SOLO PRIMO PICCO"
dati_picco1=zeros(size(dati));
dati_picco1(1:i)=dati(1:i);

pesi_picco1=0.01+zeros(size(pesi));
pesi_picco1(1:i)=pesi(1:i);

% STIMATORE
ciclo=true;
nCiclo=0;
p=p0;
while ciclo
    nCiclo=nCiclo+1;
    [p, ~, ~, exitFlag,~,~,~] = lsqnonlin(@objFitGV_picco1, p, lb, ub, options, dati_picco1, pesi_picco1,options_DSC) ;
    
    if (nCiclo>=4)||(exitFlag>0)
        ciclo=false;
    end
end
GVparametri=p';

if options_DSC.display>2
    figure(h);
    hold on
    plot(options_DSC.time,GVfunction_picco1(p,options_DSC),'r-')
    title('First peak final fit')
    pause
    try
        close(h);
    end
end

%% ------------------------------------------------------------------------
function [out]                         = objFitGV_picco1(p,dati,pesi,options)
% Funzione obiettivo da minimizzare per la funzione fitGV_picco1
vett=GVfunction_picco1(p,options);

out=(vett-dati)./pesi;


%% ------------------------------------------------------------------------
function [GV]                          = GVfunction_picco1(p,options)
% Calcola la funzione gamma-variata definita dai parametri contenuti in p.
% La funzione gamma-variata � definita dalla formula:
%
% GV(t)=A*((t-t0)^alpha)*exp(-(t-t0)/beta)
%
% parametri: p=[t0 alpha beta A]

t0    = p(1);    % t0
alpha = p(2);    % alpha
beta  = p(3);    % beta
A     = p(4);    % A

nT=length(options.time);
GV=zeros(nT,1);
for cont=1:nT
    t=options.time(cont);
    if t>t0
        GV(cont)=A*((t-t0)^alpha)*exp(-(t-t0)/beta);
    end
end