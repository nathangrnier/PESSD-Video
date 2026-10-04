% Constructs the weather shocks used in De Winne and Peersman (2021),
% Nature Climate Change

clear all; clc;

%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%
TIME = 1416;                  % Time dimension data (months since 1900)
START = 13;                   % Start sample period for estimation shocks (note: CRU >=13)
N = 1800;                     % >= total number of crops/areas in dataset
NCROPS = 7;                   % Number of crop calendars
%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%


% Read country/state/county index for each crop for global grid
% Put crop calendars in correct format

CALENDAR_INPUT=xlsread('Input_data.xlsx','Calendar','AY8:BK1800');

NN = size(CALENDAR_INPUT,1);
CROP_CALENDAR = zeros(N,TIME);

for i=1:NN
    IDcel = CALENDAR_INPUT(i,1);
    for j=1:TIME/12
        CROP_CALENDAR(IDcel,(j-1)*12+1:(j-1)*12+12) = CALENDAR_INPUT(i,2:13);
    end
end

%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%

% Read production and price weights and put in correct format
% Calculate weights

PROD_INPUT=xlsread('Input_data.xlsx','export','J2:M1800');
PRICES_INPUT=xlsread('Input_data.xlsx','prices','B2:ZI5');

NN = size(PROD_INPUT,1);
PRODUCTION = zeros(N,TIME);
PRICES = zeros(N,TIME);

for i=1:NN
    IDcel = PROD_INPUT(i,1);
    for j=1:TIME
        if PROD_INPUT(i,4)>0
           PRODUCTION(IDcel,j) = PROD_INPUT(i,2);
        end   
    end
    if PROD_INPUT(i,4)==1
       PRICES(IDcel,1:732) = PRICES_INPUT(1,1);
       PRICES(IDcel,733:TIME) = PRICES_INPUT(1,:);
    end
    if PROD_INPUT(i,4)==2
       PRICES(IDcel,1:732) = PRICES_INPUT(2,1);
       PRICES(IDcel,733:TIME) = PRICES_INPUT(2,:);
    end
    if PROD_INPUT(i,4)==3
       PRICES(IDcel,1:732) = PRICES_INPUT(3,1);
       PRICES(IDcel,733:TIME) = PRICES_INPUT(3,:);
    end
    if PROD_INPUT(i,4)==4
       PRICES(IDcel,1:732) = PRICES_INPUT(4,1);
       PRICES(IDcel,733:TIME) = PRICES_INPUT(4,:);
    end
end

%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%

% Read regional IDs

REGION_INPUT=xlsread('Input_data.xlsx','regions','B2:U1800');
REGION_MAT=xlsread('Input_data.xlsx','regionMAT','B2:U21');

REGION_INPUT(isnan(REGION_INPUT))=0;

% Calculate weights

NN = size(REGION_INPUT,1);
REG1 = zeros(N,20);           % Only region itself
REG2 = zeros(N,20);           % Global excluding region
REG3 = zeros(N,20);           % Global excluding region & neighbours

for i=1:NN
    IDcel = REGION_INPUT(i,1);
    if IDcel>0
       REG1(IDcel,1) = 1.0;
       REG2(IDcel,1) = 1.0;
       REG3(IDcel,1) = 1.0;
       for k=2:20
           if REGION_INPUT(i,k)==1
              REG1(IDcel,k) = 1.0;
           else 
              REG2(IDcel,k) = 1.0;
              REG3(IDcel,k) = 1.0;
           end
       end       
    end
end

for i=1:N
    for k=2:20
        if REG1(i,k)==1.0
           for m=2:20
               if REGION_MAT(k,m)==2
                  REG3(i,m) = 0.0;
               end
           end
        end
    end
end

REGION1 = zeros(N,TIME,20);
REGION2 = zeros(N,TIME,20);
REGION3 = zeros(N,TIME,20);

for j=1:TIME
    REGION1(:,j,:) = REG1(:,:);
    REGION2(:,j,:) = REG2(:,:);
    REGION3(:,j,:) = REG3(:,:);
end

% Select which one you want to use
% REGION1 = own weather outcome of region
% REGION2 = other regions in the world (including neighbouring)
% REGION3 = global minus own region and neighbouring regions

REGION = REGION3;

%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%

% Allocate weather outcome to the cells, weighted by harvest areas

AREA_INPUT(:,:,1) = ncread('Maize.crop.calendar.nc','harvested.area');
AREA_INPUT(:,:,2) = ncread('Maize.2.crop.calendar.nc','harvested.area');
AREA_INPUT(:,:,3) = ncread('Rice.crop.calendar.nc','harvested.area');
AREA_INPUT(:,:,4) = ncread('Rice.2.crop.calendar.nc','harvested.area');
AREA_INPUT(:,:,5) = ncread('Soybeans.crop.calendar.nc','harvested.area');
AREA_INPUT(:,:,6) = ncread('Wheat.crop.calendar.nc','harvested.area');
AREA_INPUT(:,:,7) = ncread('Wheat.Winter.crop.calendar.nc','harvested.area');

ID_CALENDAR(:,:,1) = ncread('Maize.crop.calendar.nc','index');
ID_CALENDAR(:,:,2) = ncread('Maize.2.crop.calendar.nc','index');
ID_CALENDAR(:,:,3) = ncread('Rice.crop.calendar.nc','index');
ID_CALENDAR(:,:,4) = ncread('Rice.2.crop.calendar.nc','index');
ID_CALENDAR(:,:,5) = ncread('Soybeans.crop.calendar.nc','index');
ID_CALENDAR(:,:,6) = ncread('Wheat.crop.calendar.nc','index');
ID_CALENDAR(:,:,7) = ncread('Wheat.Winter.crop.calendar.nc','index');

PRECIP_TIME_DATA = ncread('cru_ts4.04.1901.2019.pre.dat.nc','pre');
TEMP_TIME_DATA = ncread('cru_ts4.04.1901.2019.tmp.dat.nc','tmp');

PRECIP_TIME = zeros(720,360,TIME);
TEMP_TIME = zeros(720,360,TIME);

for i=1:720
    for j=1:360
        for m=13:TIME
            PRECIP_TIME(i,j,m) = PRECIP_TIME_DATA(i,361-j,m-12);
            TEMP_TIME(i,j,m) = TEMP_TIME_DATA(i,361-j,m-12);
        end
    end
end

%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%
 
AREA_INPUT(isnan(AREA_INPUT))=0;
HARVESTAREA = zeros(720,360,7);
AREA_TOT = zeros(1800,1);
GRIDlon = zeros(4320,1);
GRIDlat = zeros(1,2160);

CROPS_PRECIP_TIME = zeros(N,TIME);      % Collects the data for each t
CROPS_TEMP_TIME = zeros(N,TIME);        % Same for temperature 
    
%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%

GRIDlon(1:3,1) = 1;
GRIDlon(4318:4320,1) = 1;
for i=2:720
    GRIDlon((i-1)*6-2:(i-1)*6+3,1) = i;
end

GRIDlat(1,1:3) = 1;
GRIDlat(1,2158:2160) = 1;
for i=2:360
    GRIDlat(1,(i-1)*6-2:(i-1)*6+3) = i;
end

for i=1:NCROPS
    for j=1:4320
        for k=1:2160
            IDcel = ID_CALENDAR(j,k,i);
            if IDcel>0
               AREA_TOT(IDcel,1) = AREA_TOT(IDcel,1) + AREA_INPUT(j,k,i); 
            end
        end
    end
end

for i=1:NCROPS
    for j=1:4320
        for k=1:2160
            IDcel = ID_CALENDAR(j,k,i);
            lon = GRIDlon(j,1);
            lat = GRIDlat(1,k);
            if IDcel>0
               for m=1:TIME 
                   if PRECIP_TIME(lon,lat,m)>-1000.0
                      CROPS_PRECIP_TIME(IDcel,m) = CROPS_PRECIP_TIME(IDcel,m) + AREA_INPUT(j,k,i)/AREA_TOT(IDcel,1)*PRECIP_TIME(lon,lat,m);
                   end
                   if TEMP_TIME(lon,lat,m)>-1000.0
                      CROPS_TEMP_TIME(IDcel,m) = CROPS_TEMP_TIME(IDcel,m) + AREA_INPUT(j,k,i)/AREA_TOT(IDcel,1)*TEMP_TIME(lon,lat,m);
                   end
               end
            end
        end
    end
end
               
CROPS_PRECIP_TIME(isnan(CROPS_PRECIP_TIME))=0;
CROPS_TEMP_TIME(isnan(CROPS_TEMP_TIME))=0;

% Construct weighted weather shocks for each region

for k=1:20
    TEMP_RAW = CROPS_TEMP_TIME.*CROP_CALENDAR.*PRODUCTION.*PRICES.*REGION(:,:,k);
    TEMP_RAW2 = CROPS_TEMP_TIME.*abs(CROPS_TEMP_TIME).*CROP_CALENDAR.*PRODUCTION.*PRICES.*REGION(:,:,k);
    PRECIP_RAW = CROPS_PRECIP_TIME.*CROP_CALENDAR.*PRODUCTION.*PRICES.*REGION(:,:,k);
    PRECIP_RAW2 = CROPS_PRECIP_TIME.*abs(CROPS_PRECIP_TIME).*CROP_CALENDAR.*PRODUCTION.*PRICES.*REGION(:,:,k);

    TEMP_SUM = sum(TEMP_RAW,1);
    TEMP_SUM2 = sum(TEMP_RAW2,1);
    PRECIP_SUM = sum(PRECIP_RAW,1);
    PRECIP_SUM2 = sum(PRECIP_RAW2,1);

    TEMP_M(k,:) = transpose(TEMP_SUM);
    TEMP_M2(k,:) = transpose(TEMP_SUM2);
    PRECIP_M(k,:) = transpose(PRECIP_SUM);
    PRECIP_M2(k,:) = transpose(PRECIP_SUM2);
end

% Construct seasonal dummies and trends

DUM = zeros(TIME,11);
TREND = zeros(TIME,3);
TREND2 = zeros(TIME,33);

for i=1:TIME/12
    for j=1:11
        DUM((i-1)*12+j,j)=1.0;
    end
end

for t=1:TIME
    TREND(t,1) = t;
    TREND(t,2) = t*t;
    TREND(t,3) = t*t*t;
end

% in case there is a separate trend for each month => add TREND2 to XVAR

for t=1:TIME
    for j=1:11
        TREND2(t,1+(j-1)*3) = t*DUM(t,j);
        TREND2(t,2+(j-1)*3) = t*t*DUM(t,j);
        TREND2(t,3+(j-1)*3) = t*t*t*DUM(t,j);
    end
end

% Regress weather on dummies and trend to obtain weather shocks

XVAR = [DUM TREND];
SHOCKS_TEMP = NaN(TIME,20);
SHOCKS_TEMP2 = NaN(TIME,20);
SHOCKS_PRECIP = NaN(TIME,20);
SHOCKS_PRECIP2 = NaN(TIME,20);

LINR = fitlm(XVAR(START:TIME,:),TEMP_M(1,START:TIME));
SHOCKS_TEMP(START:TIME,1) = LINR.Residuals.Raw;
STDVTEMP = std(SHOCKS_TEMP(START:TIME,1));
SHOCKS_TEMP(START:TIME,1) = SHOCKS_TEMP(START:TIME,1)/STDVTEMP;

LINR = fitlm(XVAR(START:TIME,:),TEMP_M2(1,START:TIME));
SHOCKS_TEMP2(START:TIME,1) = LINR.Residuals.Raw;
STDVTEMP2 = std(SHOCKS_TEMP2(START:TIME,1));
SHOCKS_TEMP2(START:TIME,1) = SHOCKS_TEMP2(START:TIME,1)/STDVTEMP2;

LINR = fitlm(XVAR(START:TIME,:),PRECIP_M(1,START:TIME));
SHOCKS_PRECIP(START:TIME,1) = LINR.Residuals.Raw;
STDVPRECIP = std(SHOCKS_PRECIP(START:TIME,1));
SHOCKS_PRECIP(START:TIME,1) = SHOCKS_PRECIP(START:TIME,1)/STDVPRECIP;

LINR = fitlm(XVAR(START:TIME,:),PRECIP_M2(1,START:TIME));
SHOCKS_PRECIP2(START:TIME,1) = LINR.Residuals.Raw;
STDVPRECIP2 = std(SHOCKS_PRECIP2(START:TIME,1));
SHOCKS_PRECIP2(START:TIME,1) = SHOCKS_PRECIP2(START:TIME,1)/STDVPRECIP2;

for k=2:20
    LINR = fitlm(XVAR(START:TIME,:),TEMP_M(k,START:TIME));
    SHOCKS_TEMP(START:TIME,k) = LINR.Residuals.Raw;
    SHOCKS_TEMP(START:TIME,k) = SHOCKS_TEMP(START:TIME,k)/STDVTEMP;

    LINR = fitlm(XVAR(START:TIME,:),TEMP_M2(k,START:TIME));
    SHOCKS_TEMP2(START:TIME,k) = LINR.Residuals.Raw;
    SHOCKS_TEMP2(START:TIME,k) = SHOCKS_TEMP2(START:TIME,k)/STDVTEMP2;

    LINR = fitlm(XVAR(START:TIME,:),PRECIP_M(k,START:TIME));
    SHOCKS_PRECIP(START:TIME,k) = LINR.Residuals.Raw;
    SHOCKS_PRECIP(START:TIME,k) = SHOCKS_PRECIP(START:TIME,k)/STDVPRECIP;

    LINR = fitlm(XVAR(START:TIME,:),PRECIP_M2(k,START:TIME));
    SHOCKS_PRECIP2(START:TIME,k) = LINR.Residuals.Raw;
    SHOCKS_PRECIP2(START:TIME,k) = SHOCKS_PRECIP2(START:TIME,k)/STDVPRECIP2;
end

% Transform to quarterly data

SHOCKS_TEMP_Q = NaN(TIME/3,20);
SHOCKS_TEMP2_Q = NaN(TIME/3,20);
SHOCKS_PRECIP_Q = NaN(TIME/3,20);
SHOCKS_PRECIP2_Q = NaN(TIME/3,20);

for k=1:20
    for i=1:TIME/3
        SHOCKS_TEMP_Q(i,k) = mean(SHOCKS_TEMP((i-1)*3+1:(i-1)*3+3,k));
        SHOCKS_TEMP2_Q(i,k) = mean(SHOCKS_TEMP2((i-1)*3+1:(i-1)*3+3,k));
        SHOCKS_PRECIP_Q(i,k) = mean(SHOCKS_PRECIP((i-1)*3+1:(i-1)*3+3,k));
        SHOCKS_PRECIP2_Q(i,k) = mean(SHOCKS_PRECIP2((i-1)*3+1:(i-1)*3+3,k));
    end
end


