from __future__ import print_function
import warnings
warnings.filterwarnings("ignore")
import matplotlib
matplotlib.use('Agg')
import numpy as np
import numpy.ma as ma
import pylab as plt
from trackeddy.datastruct import *
from trackeddy.geometryfunc import *
from trackeddy.init import *
from trackeddy.physics import *
from trackeddy.printfunc import *
from trackeddy.savedata import *
import seawater as sw
from scipy import ndimage
import sys
import time


def scan_eddym(ssh,lon,lat,levels,date,areamap,mask='',destdir='',physics='',eddycenter='masscenter',ellipsrsquarefit=0.95,eccenfit=0.85,gaussrsquarefit=0.65,mode='gaussian',basemap=False,checkgauss=True,checkarea=True,usefullfit=False,diagnostics=False,plotdata=False,pprint=True):
    '''
    *************Scan Eddym***********
    Function to identify each eddy using closed contours,
    also this function checks if the elipse adjusted have
    a consistent eccentricity, vorticty and other parameters.
    Usage:
    ssh= Sea Surface Height in cm
    lon,lat=longitude and latitude of your grid.
    levels=where the code will find the closed contours.
    date=date in julian days
    areamap=Section of interest
    mask=Continent mask
    
    Example:
    ssh=Read netCDF4 data with mask or create a mask for your data
    lon=Import your longitude coordinates, if your grid is regular, you can use a linspace instead
    lat=Import your latitude coordinates (same as above).
    levels=List of the levels in which ones you want to find the eddies
    date=Date as Julian Days
    areamap=array([[0,len(lon)],[0,len(lat)]]) Array with the index of your area of interest.
    I used some auxilar functions, each one has his respective author.
    Author: Josue Martinez Moreno, 2017
    '''
    #tic=time.time()
    ellipse_path=[]
    contour_path=[]
    mayoraxis_eddy=[]
    minoraxis_eddy=[]
    gaussianfitdict=[]
    shapedata=np.shape(ssh)
    if ssh is ma.masked:
        print('Invalid ssh data, must be masked')
        return
    if shapedata == [len(lat), len(lon)]:
        print('Invalid ssh data size, should be [length(lat) length(lon]')
        return
    if np.shape(areamap) == shapedata:
        if np.shape(areamap) == [1, 1] | len(areamap) != len(lat):
            print('Invalid areamap, using NaN for eddy surface area')
        return
    if len(levels)!= 2:
        print('Invalid len of levels, please use the function for multiple levels or use len(levels)==2')
        return
    #Saving mask for future post-processing.  
    
    if mask!='':
        ssh=np.ma.masked_array(ssh, mask)
    sshnan=ssh.filled(np.nan)
    
    #Join sintetic fields for each level (Not useful for the final goal)
    #if len(shapedata)==3:
    #    syntetic_ssha=np.zeros(shapedata[1],shapedata[2])
    #else:
    #    syntetic_ssha=np.zeros(shapedata)
    
    #Obtain the contours of a surface (contourf), this aproach is better than the contour.
    if len(np.shape(lon))== 1 and len(np.shape(lat)) == 1:
        Lon,Lat=np.meshgrid(lon,lat)
    else:
        Lon,Lat=lon,lat
    
    min_x=Lon[0,0]
    min_y=Lat[0,0]
    max_x=Lon[-1,-1]
    max_y=Lat[-1,-1]
    
    if basemap==True:
        fig, ax = plt.subplots(figsize=(10,10))
        m = Basemap(projection='ortho',lat_0=-90,lon_0=-100,resolution='c')
        m.drawcoastlines()
        m.fillcontinents(color='black',lake_color='aqua')
        m.drawmeridians(np.arange(0,360,30),labels=[1,1,0,0],fontsize=10)
        lonm,latm=m(Lon,Lat)
    
        if len(shapedata)==3:
            m.contourf(lonm[areamap[1,0]:areamap[1,1],areamap[0,0]:areamap[0,1]],\
                       latm[areamap[1,0]:areamap[1,1],areamap[0,0]:areamap[0,1]],\
                    sshnan[date,areamap[1,0]:areamap[1,1],areamap[0,0]:areamap[0,1]],levels=levels)
            plt.show()

        else:
            m.contourf(lonm[areamap[1,0]:areamap[1,1],areamap[0,0]:areamap[0,1]],\
                       latm[areamap[1,0]:areamap[1,1],areamap[0,0]:areamap[0,1]],\
                    sshnan[areamap[1,0]:areamap[1,1],areamap[0,0]:areamap[0,1]],levels=levels)
            plt.show()
            
    if len(shapedata)==3:
        CS=plt.contourf(lon[areamap[0,0]:areamap[0,1]],lat[areamap[1,0]:areamap[1,1]],\
                sshnan[date,areamap[1,0]:areamap[1,1],areamap[0,0]:areamap[0,1]],levels=levels)
    else:
        CS=plt.contourf(lon[areamap[0,0]:areamap[0,1]],lat[areamap[1,0]:areamap[1,1]],\
                sshnan[areamap[1,0]:areamap[1,1],areamap[0,0]:areamap[0,1]],levels=levels)
    # Close the contour plot.
    plt.close()
    CONTS=CS.allsegs[:][:]
    #Loop in contours of the levels defined.
    total_contours=0
    eddyn=0
    threshold=7
    numverlevels=np.shape(CONTS)[0]
    #print(time.time()-tic)
    for ii in range(0,numverlevels):
        CONTSlvls=CONTS[ii]
        numbereddies=np.shape(CONTSlvls)[0]
        for jj in range(0,numbereddies):
            if diagnostics==True:
                print("----- New Eddy -----")
            CONTeach=CONTSlvls[jj]
            #print(len(CONTeach[:,1]))
            if (len(CONTeach[:,0]) | len(CONTeach[:,1])) <= 10:
                xx=np.nan
                yy=np.nan
                center=[np.nan,np.nan]
                check=False
            else:
                ellipse,status=fit_ellipse(CONTeach[:,0],CONTeach[:,1],diagnostics=diagnostics)
                checke=False
                if status==True:
                    checke=False
                    ellipseadjust,checke=ellipsoidfit(CONTeach[:,1],ellipse['ellipse'][1],\
                                                  ellipsrsquarefit=ellipsrsquarefit,\
                                                  diagnostics=diagnostics)
                if checke==True:
                    xidmin,xidmax=find2l(lon,lon,CONTeach[:,0].min(),CONTeach[:,0].max())
                    yidmin,yidmax=find2l(lat,lat,CONTeach[:,1].min(),CONTeach[:,1].max())
                    
                    if xidmin<=threshold-1:
                        xidmin=+threshold-1
                    elif xidmax>=len(lon)-threshold:
                        xidmax=len(lon)-threshold
                    if yidmin<=threshold-1:
                        yidmin=threshold-1
                    elif yidmax>=len(lat)-threshold:
                        yidmax=len(lat)-threshold
                    lon_contour=lon[xidmin-threshold+1:xidmax+threshold]
                    lat_contour=lat[yidmin-threshold+1:yidmax+threshold]
                    
                    #center=[int((yidmax-yidmin)/2)+threshold-1,int((xidmax-xidmin)/2)+threshold-1]
                    cmindex=find(CONTeach[:,1],CONTeach[:,1].max())
                    xmindex,ymindex=find2l(lon,lat,CONTeach[cmindex,0],CONTeach[cmindex,1])
                    
                    
                    centertop=[ymindex-yidmin+threshold-2,xmindex-xidmin+threshold-1]
                    
                    if len(shapedata)==3:
                        ssh4gauss=sshnan[date,yidmin-threshold+1:yidmax+threshold,xidmin-threshold+1:xidmax+threshold]
                        ssh_in_contour=insideness_contour(ssh4gauss,centertop,levels,maskopt='contour',diagnostics=diagnostics)
                    else:
                        ssh4gauss=sshnan[yidmin-threshold+1:yidmax+threshold,xidmin-threshold+1:xidmax+threshold]
                        ssh_in_contour=insideness_contour(ssh4gauss,centertop,levels,maskopt='contour',diagnostics=diagnostics)
                    
                    
#                    f, (ax1, ax2) = plt.subplots(1, 2,figsize=(8, 4))
#                    ax1.pcolormesh(ssh_in_contour)
#                    contourgrad=np.sqrt(np.gradient(ssh_in_contour)[0]**2+np.gradient(ssh_in_contour)[1]**2)
#                    im=ax2.contourf(contourgrad,levels=np.linspace(contourgrad.min(),contourgrad.max(),10))
                    #print(np.where(contourgrad==contourgrad.min()))
                    #f.colorbar(im, ax=ax2)
                    #plt.show()
                    
                    #except:
                    #    print('No detected connections')
                    #USE ALL THE DOMAIN    
                    #ssh_in_contour=sshnan
                    #lon_contour=lon
                    #lat_contour=lat
                    #plt.pcolormesh(ssh_in_contour)
                    #plt.show()
                    center = [ellipse['X0_in'],ellipse['Y0_in']]
                    phi = ellipse['phi']
                    axes = [ellipse['a'],ellipse['b']]
                    R = np.arange(0,2.1*np.pi, 0.1)
                    a,b = axes
                    #Ellipse coordinates.
                    xx = ellipse['ellipse'][0]
                    yy = ellipse['ellipse'][1]
                    
                    mayoraxis = ellipse['majoraxis']
                    minoraxis = ellipse['minoraxis']
                    
                    #Area of Contours (contarea) and ellipse (ellipsarea)
                    #contarea=PolyArea(CONTeach[:,0],CONTeach[:,1])
                    #ellipsarea=PolyArea(xx,yy)
                    
                    # Linear Eccentricity check
                    eccen=eccentricity(a,b)
                    #Record and check how many grid points have land or masked values
                    
                    #Check coverage of land 
                    checkland=eddylandcheck(CONTeach,center,lon_contour,lat_contour,ssh_in_contour)
                    #Check Rossby Area (Rossby_radius^2)
                    areachecker,ellipsarea,contarea=checkmesoscalearea(checkarea,lat_contour,\
                                                                       xx,yy,\
                                                                       CONTeach[:,0],CONTeach[:,1])
                    if eddycenter == 'maximum':
                        center_eddy=contourmaxvalue(ssh_in_contour,lon_contour,\
                                             lat_contour,levels,date,threshold)
                        center_eddy[3]=center_eddy[3]+xidmin-threshold+1
                        center_eddy[4]=center_eddy[4]+yidmin-threshold+1
                        
                        center_extrem=center_eddy
                        
                    elif eddycenter == 'masscenter':
                        center_eddy=centroidvalue(CONTeach[:,0],CONTeach[:,1],\
                                            ssh_in_contour,lon_contour,\
                                            lat_contour,levels,date,threshold)
                        center_extrem=contourmaxvalue(ssh_in_contour,lon_contour,\
                                                    lat_contour,levels,date)
                        center_extrem[3]=center_extrem[3]+xidmin-threshold+1
                        center_extrem[4]=center_extrem[4]+yidmin-threshold+1
                        #try:
                        #    center_extrem=contourmaxvalue(ssh_in_contour,lon_contour,\
                        #                            lat_contour,levels,date)
                        #except:
                        #    center_extrem=center_eddy
                    #print(center_extrem[:2],lon[center_extrem[3]],lat[center_extrem[4]])
                    if checkland==False:
                        check=False
                    else:
                        checkM=False
                        checkm=False 
                        if contarea>=ellipsarea:
                            #if contarea/1.5>ellipsarea:
                            #    check=False
                            if eccen<eccenfit and eccen>0:
                                if ellipsarea < areachecker and contarea < areachecker:
                                    if checkgauss==True:
                                        if len(shapedata)==3:
                                            profile,checkM=extractprofeddy(mayoraxis,\
                                                           ssh4gauss,lon_contour,lat_contour,50,\
                                                           gaus='One',kind='linear',\
                                                           gaussrsquarefit=gaussrsquarefit,\
                                                           diagnostics=diagnostics)
                                            if checkM==True:
                                                profile,checkm=extractprofeddy(minoraxis,\
                                                               ssh4gauss,lon_contour,\
                                                               lat_contour,50,\
                                                               gaus='One',kind='linear',\
                                                               gaussrsquarefit=gaussrsquarefit,\
                                                               diagnostics=diagnostics)
                                        else:
                                            profile,checkM=extractprofeddy(mayoraxis,\
                                                           ssh4gauss,lon_contour,lat_contour,50,\
                                                           gaus='One',kind='linear',\
                                                           gaussrsquarefit=gaussrsquarefit,\
                                                           diagnostics=diagnostics)
                                            if checkM==True:
                                                profile,checkm=extractprofeddy(minoraxis,\
                                                               ssh4gauss,lon_contour,\
                                                               lat_contour,50,\
                                                               gaus='One',kind='linear',\
                                                               gaussrsquarefit=gaussrsquarefit,\
                                                               diagnostics=diagnostics)
                                        #print('Time elapsed ellipsoidfit:',str(time.time()-tic))
                                        if checkM==True and checkm==True: 
                                            check=True
                                            if levels[0] > 0:
                                                level=levels[0]
                                                extremvalue=ssh_in_contour.max()
                                            else:
                                                level=levels[1]
                                                extremvalue=ssh_in_contour.min()
                                            
                                            #initial_guess=[extremvalue,center_extrem[0],center_extrem[1],\
                                            #               a,b,phi,0,0,0]
                                            initial_guess=[a,b,phi,0,0,0]
                                            #initial_guess=[1,1,0,0,0,0]
                                            gausssianfitp,R2=fit2Dcurve(ssh_in_contour,\
                                                          lon_contour,lat_contour,\
                                                          extremvalue,center_extrem[0],center_extrem[1],\
                                                          level,initial_guess=initial_guess,date='',\
                                                          mode=mode,diagnostics=diagnostics)
                                            if R2 < gaussrsquarefit and R2 < 1:
                                                check=False
                                            #syntetic_ssha[yidmin-6:yidmax+7,xidmin-6:xidmax+7]=\
                                            #        syntetic_ssha[yidmin-6:yidmax+7,xidmin-\
                                            #                      6:xidmax+7]+gausssianfitp
                                            #USE ALL THE DOMAIN    
                                            #syntetic_ssha=gausssianfitp
                                            
                                        else:
                                            check=False
                                    else:
                                        print('Checkgauss need to be True to reconstruct the field.')
                                else:
                                    check=False
                            else:
                                check=False
                        elif contarea<ellipsarea:
                            #if contarea<ellipsarea/1.5:
                                #print 'Removing contour, thisone is really overestimate'
                            #    check=False
                            #elif eccen<0.95 and eccen>0.4:
                            if eccen<eccenfit and eccen>0:
                                if ellipsarea < areachecker and contarea<areachecker:
                                    if checkgauss==True:
                                        if len(shapedata)==3:
                                            profile,checkM=extractprofeddy(mayoraxis,\
                                                           ssh4gauss,lon_contour,lat_contour,50,\
                                                           gaus='One',kind='linear',\
                                                           gaussrsquarefit=gaussrsquarefit,\
                                                           diagnostics=diagnostics)
                                            if checkM==True:
                                                profile,checkm=extractprofeddy(minoraxis,\
                                                               ssh4gauss,lon_contour,\
                                                               lat_contour,50,\
                                                               gaus='One',kind='linear',\
                                                               gaussrsquarefit=gaussrsquarefit,\
                                                               diagnostics=diagnostics)
                                        else:
                                            profile,checkM=extractprofeddy(mayoraxis,\
                                                           ssh4gauss,lon_contour,lat_contour,50,\
                                                           gaus='One',kind='linear',\
                                                           gaussrsquarefit=gaussrsquarefit,\
                                                           diagnostics=diagnostics)
                                            if checkM==True:
                                                profile,checkm=extractprofeddy(minoraxis,\
                                                               ssh4gauss,lon_contour,\
                                                               lat_contour,50,\
                                                               gaus='One',kind='linear',\
                                                               gaussrsquarefit=gaussrsquarefit,\
                                                               diagnostics=diagnostics)
                                      #print('Time elapsed ellipsoidfit:',str(time.time()-tic))
                                        if checkM==True and checkm==True:
                                            check=True
                                            if levels[0] > 0:
                                                level=levels[0]
                                                extremvalue=ssh_in_contour.max()
                                            else:
                                                level=levels[1]
                                                extremvalue=ssh_in_contour.min()
                                                
                                            #initial_guess=[extremvalue,center_extrem[0],center_extrem[1],\
                                            #               a,b,phi,0,0,0]
                                            initial_guess=[a,b,phi,0,0,0]
                                            #initial_guess=[1,1,0,0,0,0]
                                            gausssianfitp,R2=fit2Dcurve(ssh_in_contour,\
                                                          lon_contour,lat_contour,\
                                                          extremvalue,center_extrem[0],center_extrem[1],\
                                                          level,initial_guess=initial_guess,date='',\
                                                          mode=mode,diagnostics=diagnostics)
                                            if R2 < gaussrsquarefit and R2 < 1:
                                                check=False
                                            #syntetic_ssha[yidmin-6:yidmax+7,xidmin-6:xidmax+7]=\
                                            #        syntetic_ssha[yidmin-6:yidmax+7,xidmin-\
                                            #                      6:xidmax+7]+gausssianfitp
                                            #USE ALL THE DOMAIN
                                            #syntetic_ssha=gausssianfitp
                                        else:
                                            check=False
                                    else:
                                        print('Checkgauss need to be True')
                                else:
                                    check=False
                            else:
                                #print 'Removing contour, thisone is really underestimate'
                                check=False
                                ellipseadjust=np.nan
                        else:
                            check=False
                    if check==True:# or check==False:
                        if usefullfit==False and mode=='gaussian':
                            gausssianfitp[-1]=0
                            gausssianfitp[-2]=0
                            gausssianfitp[-3]=0
                        ellipse_path.append([xx,yy])
                        contour_path.append([CONTeach[:,0],CONTeach[:,1]])
                        mayoraxis_eddy.append([mayoraxis[0],mayoraxis[1]])
                        minoraxis_eddy.append([minoraxis[0],minoraxis[1]])
                        gaussianfitdict.append([gausssianfitp])
                        #Switch from the ellipse center to the position of 
                        #the maximum value inside de contour
                        if eddyn==0:
                            position_selected=[center_eddy]
                            position_max=[center_extrem]
                            position_ellipse=[center]
                            total_eddy=[eddyn]
                            area=[contarea]
                            angle=[phi]
                            if CS.levels[0] > 0:
                                level=CS.levels[0]
                            else:
                                level=CS.levels[1]
                            levelm=[level]
                        else:
                            position_selected=np.vstack((position_selected,center_eddy))
                            position_max=np.vstack((position_max,center_extrem))
                            position_ellipse=np.vstack((position_ellipse,center))
                            total_eddy=np.vstack((total_eddy,eddyn))
                            area=np.vstack((area,contarea))
                            angle=np.vstack((angle,phi))
                            
                            if CS.levels[0] > 0:
                                levelprnt=CS.levels[0]
                                levelm=np.vstack((levelm,levelprnt))
                            else:
                                levelprnt=CS.levels[1]
                                levelm=np.vstack((levelm,levelprnt))
                            
                        eddyn=eddyn+1
                    #diagnostics=True
                    if diagnostics == True:# and  check == True:
                        print("Eddy Number (No time tracking):", eddyn)
                        print("Ellipse parameters")
                        print("Ellipse center = ",  center)
                        print("Mass center = ",  center_eddy)
                        print("angle of rotation = ",  phi)
                        print("axes (a,b) = ", axes)
                        print("Eccentricity = ",eccen)
                        print("Area (cont,ellips) = ",contarea,ellipsarea)
                        print("Ellipse adjust = ",ellipseadjust,checke)
                        print("Mayor Gauss fit = ",checkM)
                        print("Minor Gauss fit = ",checkm)
                        print("Conditions | Area | Ellipse | Eccen | Gaussians ")
                        print("           | ", ellipsarea < areachecker and contarea < areachecker ,\
                              " | ", checke ,"| ", eccen<eccenfit ,"| ",checkM == True and checkm == True)
                        
                    if diagnostics == True: #and plotdata == True:
                        f, (ax1, ax2) = plt.subplots(1, 2,figsize=(13, 6))
                        if len(shapedata)==3:
                            ax1.contourf(lon[areamap[0,0]:areamap[0,1]],lat[areamap[1,0]:areamap[1,1]],\
                                ssh[date,areamap[1,0]:areamap[1,1],areamap[0,0]:areamap[0,1]])
                            cc=ax2.pcolormesh(lon[areamap[0,0]:areamap[0,1]],\
                                              lat[areamap[1,0]:areamap[1,1]],\
                              ssh[date,areamap[1,0]:areamap[1,1],areamap[0,0]:areamap[0,1]],\
                              vmin=ssh[date,areamap[1,0]:areamap[1,1],areamap[0,0]:areamap[0,1]].min(),\
                              vmax=ssh[date,areamap[1,0]:areamap[1,1],areamap[0,0]:areamap[0,1]].max())
                            cca=ax2.contour(lon[areamap[0,0]:areamap[0,1]],\
                                            lat[areamap[1,0]:areamap[1,1]],\
                                            ssh[date,areamap[1,0]:areamap[1,1],\
                                            areamap[0,0]:areamap[0,1]],levels=levels,cmap='jet')
                            ax2.clabel(cca, fontsize=9, inline=1)
                        else:
                            cca=ax1.contourf(lon[areamap[0,0]:areamap[0,1]],\
                                             lat[areamap[1,0]:areamap[1,1]],\
                                             sshnan[areamap[1,0]:areamap[1,1],areamap[0,0]:areamap[0,1]],levels=levels)
                            ax1.plot(CONTeach[:,0],CONTeach[:,1],'-r')
                            ax2.plot(CONTeach[:,0],CONTeach[:,1],'-r')
                            ax2.pcolormesh(lon[areamap[0,0]:areamap[0,1]],\
                                           lat[areamap[1,0]:areamap[1,1]],\
                                           sshnan[areamap[1,0]:areamap[1,1],\
                                           areamap[0,0]:areamap[0,1]],vmin=-20,vmax=20)
                            plt.show()
                            f, (ax1, ax2) = plt.subplots(1, 2,figsize=(13, 6))
                            ax1.contourf(lon[areamap[0,0]:areamap[0,1]],\
                                         lat[areamap[1,0]:areamap[1,1]],\
                                         ssh[areamap[1,0]:areamap[1,1],areamap[0,0]:areamap[0,1]])
                            cc=ax2.pcolormesh(lon[areamap[0,0]:areamap[0,1]],\
                                              lat[areamap[1,0]:areamap[1,1]],\
                              ssh[areamap[1,0]:areamap[1,1],areamap[0,0]:areamap[0,1]],\
                              vmin=ssh[areamap[1,0]:areamap[1,1],areamap[0,0]:areamap[0,1]].min(),\
                              vmax=ssh[areamap[1,0]:areamap[1,1],areamap[0,0]:areamap[0,1]].max())
                            cca=ax2.contour(lon[areamap[0,0]:areamap[0,1]],\
                                            lat[areamap[1,0]:areamap[1,1]],\
                                            ssh[areamap[1,0]:areamap[1,1],areamap[0,0]:areamap[0,1]],levels=levels,cmap='jet')
                            ax2.clabel(cca, fontsize=9, inline=1)
                        ax1.plot(CONTeach[:,0],CONTeach[:,1],'*r')
                        ax1.plot(xx,yy,'-b')
                        ax1.plot(center[0],center[1],'ob')
                        f.subplots_adjust(right=0.8)
                        cbar_ax = f.add_axes([0.85, 0.15, 0.05, 0.7])
                        f.colorbar(cc, cax=cbar_ax)
                        ax2.plot(CONTeach[:,0],CONTeach[:,1],'-r')
                        ax2.plot(xx,yy,'-b')
                        ax2.plot(center[0],center[1],'ob')
                        idxelipcheck,idyelipcheck=find2l(lon,lat,center[0],center[1])
                        ax2.plot(lon[idxelipcheck],lat[idyelipcheck],'om')
                        ax2.plot(center_eddy[0],center_eddy[1],'oc')
                        ax2.plot(center_extrem[0],center_extrem[1],'*g')
                        ax2.set_ylim([CONTeach[:,1].min(),CONTeach[:,1].max()])
                        ax2.set_xlim([CONTeach[:,0].min(),CONTeach[:,0].max()])
                        plt.show()
                        plt.close()
                        
                total_contours=total_contours+1
            if pprint==True:
                string='Total of contours was: %d -' +\
                       'Total of eddies: %d - Level: %.1f '%(total_contours,eddyn,level)
                pt =Printer(); pt.printtextoneline(string)
        try:
            position_selected=np.array(position_selected)
            position_max=np.array(position_max)
            position_ellipse=np.array(position_ellipse)
#            if type(level)==float or type(level)==int or isinstance(level, float):
#                level=[np.array(level)]
#            else:
            levelm=np.array(levelm)
            mayoraxis_eddy=np.array(mayoraxis_eddy)
            minoraxis_eddy=np.array(minoraxis_eddy)
            gaussianfitdict=np.array(gaussianfitdict)
            eddys=dict_eddym(contour_path,ellipse_path,position_selected,\
                             position_max,position_ellipse,\
                             mayoraxis_eddy,minoraxis_eddy,\
                             area,angle,total_eddy,levelm,gaussianfitdict)
            check=True
            
        except:
            eddys=0
            check=False
        #if destdir!='':
        #    save_data(destdir+'day'+str(date)+'_one_step_cont'+str(total_contours)+'.dat', variable)
    return eddys,check,numbereddies
    
def scan_eddyt(ssh,lat,lon,levels,date,areamap,destdir='',okparm='',diagnostics=False):
    '''
    SCAN_EDDY Scan all of the ssh data passed in (will function correctly if data passed in is a subset)
    ssh: ssh cube with nans for land
    lat: A 1D array of double's that gives the latitude for a given index in ssh data , should be equal to size(ssh, 1)
    lon: A 1D array of double's that gives the longitude for a given index in ssh data, should be equal to size(ssh, 2)
    dates: A 1D array of the dates of ssh data, length should be equal to shape(ssh)[0] 
    destdir: destination directory to save eddies
    '''
    if len(np.shape(ssh))==3:
        if date==0:
            print('Please change the date to the number of iteratios you want')
    else:
        print('Please use the other function scan_eddym')
        return
    for tt in range(0,date):
        print("**********Starting iteration ",tt,"**********")
        eddys=scan_eddym(ssh[tt,:,:],lon,lat,levels,tt,areamap,destdir='',okparm=okparm,diagnostics=diagnostics)
        if tt==0:
            eddytd=dict_eddyt(tt,eddys)
        else:
            eddytd=dict_eddyt(tt,eddys,eddytd) 
        print("**********Finished iteration ",tt,"**********")
    if destdir!='':
        save_data(destdir+str(date),eddies)
    return eddytd

def exeddydt(eddydt,lat,lon,data,threshold,inside='',diagnostics=False):
    '''*************Extract Eddy***********
    Function to extract each eddy in multiple timesteps using closed contours.
    Usage:
    eddydt= Eddy data structure
    lon,lat=longitude and latitude of your grid.
    levels=Level of the contour
    Example:
    Author: Josue Martinez Moreno, 2017
    '''
    justeddy=np.zeros(np.shape(data))
    print('*******Removing of eddies******')
    for key, value in eddydt.items():
        #print(key)
        if type(value['time'])==int:
            time=[value['time']]
        elif len(value['time'])==1:
            time=[value['time'][0]]
        else:
            time=[]
            for ii in value['time']:
                time.append(ii[0])
        ct=0 
        for tt in time:
            if len(value['level'])!= 1:
                level=value['level'][ct]
            else:
                level=value['level']
                
            lonmi=value['contour'][ct][0].min()
            lonma=value['contour'][ct][0].max()
            latmi=value['contour'][ct][1].min()
            latma=value['contour'][ct][1].max()
            
            mimcx,mimcy=find2l(lon,lat,lonmi,latmi)
            mamcx,mamcy=find2l(lon,lat,lonma,latma)
            
            loncm=lon[mimcx-threshold:mamcx+1+threshold]
            latcm=lat[mimcy-threshold:mamcy+1+threshold]
            
            cmindex=find(value['contour'][ct][1],latma)
            
            xmindex,ymindex=find2l(lon,lat,value['contour'][ct][0][cmindex],\
                                   value['contour'][ct][1][cmindex])
            
            if mimcx<threshold:
                mimcx=7
            if mimcy<threshold:
                mimcy=7
                
            databox=data[tt,mimcy-threshold:mamcy+1+threshold,mimcx-threshold:mamcx+1+threshold]
            
            centertop=[ymindex-mimcy+threshold-2,xmindex-mimcx+threshold-1]
            
            if inside =='none':
                datacm=insideness_contour(databox,centertop,level,maskopt=inside,diagnostics=diagnostics)
                datacm=ma.filled(datacm,fill_value=0)
            elif inside =='max':
                datacm=insideness_contour(databox,centertop,level,maskopt=inside,diagnostics=diagnostics)
                datacm=ma.filled(datacm,fill_value=0)
            elif inside =='contour':
                datacm=insideness_contour(databox,centertop,level,maskopt=inside,diagnostics=diagnostics)
                datacm=ma.filled(datacm,fill_value=0)
            elif inside == '':
                datacm= databox  -level
                if level > 0:
                    datacm[datacm<=0]=0
                    datacm[datacm>=1000]=0
                elif level < 0:
                    datacm[datacm>=0]=0
                    datacm[datacm<=-1000]=0
            else:
                datacm=databox*1
                insidecm=inside[tt,mimcy-threshold:mamcy+1+threshold,mimcx-threshold:mamcx+1+threshold]*1
                if level > 0:
                    insidecm[insidecm<=level]=0
                    insidecm[insidecm>=level]=1
                elif level < 0:
                    insidecm[insidecm>=level]=0
                    insidecm[insidecm<=level]=1
                #if np.shape(insidecm)!=np.shape(datacm):
                #    print('Inside and general field should have the same shape')
                #else:
                datacm=datacm*insidecm
            
            if diagnostics==True:
                plt.figure()
                plt.pcolormesh(lon[mimcx-threshold:mamcx+1+threshold],lat[mimcy-threshold:mamcy+1+threshold],datacm)
                #plt.contourf(lon[mimcx-threshold:mamcx+1+threshold],lat[mimcy-threshold:mamcy+1+threshold],insidecm)
                plt.colorbar()
                cca=plt.contourf(lon[mimcx-threshold:mamcx+1+threshold],lat[mimcy-threshold:mamcy+1+threshold],datacm,alpha=0.5)
                plt.plot(value['contour'][ct][0],value['contour'][ct][1],'-m')
                plt.show()
            
            data[tt,mimcy-threshold:mamcy+1+threshold,mimcx-threshold:mamcx+1+threshold]=            data[tt,mimcy-threshold:mamcy+1+threshold,mimcx-threshold:mamcx+1+threshold]-datacm
            justeddy[tt,mimcy-threshold:mamcy+1+threshold,mimcx-threshold:mamcx+1+threshold]=justeddy[tt,mimcy-threshold:mamcy+1+threshold,mimcx-threshold:mamcx+1+threshold]+datacm
            
            ct=ct+1 
    diagnostics=True
    if diagnostics==True:
        plt.figure()
        plt.pcolormesh(justeddy[0,:,:])
        plt.show()
    print('*******End the Removing of eddies******')
    return justeddy

def exeddy(eddydt,lat,lon,data,ct,threshold,inside='',diagnostics=False):
    '''*************Extract Eddy***********
    Function to extract the values of the eddies inside the closed contours.
    Usage:
    eddydt= Eddy data structure
    lon,lat=longitude and latitude of your grid.
    levels=Level of the contour
    Example:
    
    Author: Josue Martinez Moreno, 2017
    '''
    justeddy=np.zeros(np.shape(data))
    print('*******Removing of eddies******')
    for key, value in eddydt.items():
        #print(type(value['level']))
        #print(len(value['level']))
        if len(value['level'])!= 1:
            level=value['level'][ct]
        else:
            level=value['level']
        #print(level)
        rct=value['time']
        #print(len(value['time']))
        if type(value['time'])==int:
            lonmi=np.array(value['contour'][0][0]).min()
            lonma=np.array(value['contour'][0][0]).max()
            latmi=np.array(value['contour'][0][1]).min()
            latma=np.array(value['contour'][0][1]).max()
        else:
            lonmi=value['contour'][ct][0].min()
            lonma=value['contour'][ct][0].max()
            latmi=value['contour'][ct][1].min()
            latma=value['contour'][ct][1].max()
            
        mimcx,mimcy=find2l(lon,lat,lonmi,latmi)
        mamcx,mamcy=find2l(lon,lat,lonma,latma)
        loncm=lon[mimcx-threshold:mamcx+1+threshold]
        latcm=lat[mimcy-threshold:mamcy+1+threshold]

        if mimcx==0:
            mimcx=1
        if mimcy==0:
            mimcy=1
        if inside == '':
            datacm=data[mimcy-threshold:mamcy+1+threshold,mimcx-threshold:mamcx+1+threshold]-level
            if level > 0:
                datacm[datacm<=0]=0
                datacm[datacm>=1000]=0
            elif level < 0:
                datacm[datacm>=0]=0
                datacm[datacm<=-1000]=0
        else:
            datacm=data[mimcy-threshold:mamcy+1+threshold,mimcx-threshold:mamcx+1+threshold]*1
            insidecm=inside[mimcy-threshold:mamcy+1+threshold,mimcx-threshold:mamcx+1+threshold]*1
            if level > 0:
                insidecm[insidecm<=level]=0
                insidecm[insidecm>=level]=1
            elif level < 0:
                insidecm[insidecm>=level]=0
                insidecm[insidecm<=level]=1
            #if np.shape(insidecm)!=np.shape(datacm):
            #    print('Inside and general field should have the same shape')
            #else:
            datacm=datacm*insidecm
            
        if diagnostics==True:
            plt.figure()
            plt.pcolormesh(lon[mimcx-threshold:mamcx+1+threshold],lat[mimcy-threshold:mamcy+1+threshold],datacm)
            plt.contourf(lon[mimcx-threshold:mamcx+1+threshold],lat[mimcy-threshold:mamcy+1+threshold],insidecm)
            plt.colorbar()
            cca=plt.contourf(lon[mimcx-threshold:mamcx+1+threshold],lat[mimcy-threshold:mamcy+1+threshold],datacm,alpha=0.5)
            plt.plot(value['contour'][0],value['contour'][1],'-m')
            plt.show()
            plt.figure()
            plt.pcolormesh(justeddy)
            plt.show()
            plt.close()
            
        justeddy[mimcy-threshold:mamcy+1+threshold,mimcx-threshold:mamcx+1+threshold]=datacm
    print('*******End the Removing of eddies******')
    return justeddy
def analyseddyzt(data,x,y,t0,t1,tstep,maxlevel,minlevel,dzlevel,data_meant='',areamap='',mask='',physics='',eddycenter='masscenter',eccenfit=0.95,gaussrsquarefit=0.5,ellipsrsquarefit=0.9,checkgauss=True,checkarea=True,mode='gaussian',sfilter='none',destdir='',saveformat='nc',diagnostics=False,plotdata=False,pprint=False):
    '''
    *************Analys eddy in z and t ***********
    Function to identify each eddy using closed contours, 
    moving in time and contour levels
    Usage:
    
    Example:

    Author: Josue Martinez Moreno, 2017
    '''
    if len(np.shape(data))<3:
        print('If you whant to analyze in time the data need to be 3d [i.e. data(t,x,y)]')
        #return
    if areamap=='':
        areamap=np.array([[0,len(x)],[0,len(y)]])
    if mask=='':
        if ma.is_masked(data):
            if len(np.shape(data))<3:
                mask=ma.getmask(data[:,:])
                data=data.filled(fill_value=0)
            else:
                mask=ma.getmask(data[0,:,:])
                data=data.filled(fill_value=0)
        else:
            if len(np.shape(data))<3:
                mask=np.zeros(np.shape(data[:,:]))
            else:
                mask=np.zeros(np.shape(data[0,:,:]))
    pp =  Printer(); 
    numbereddieslevels=0
    for ii in range(t0,t1,tstep):
        checkcount=0  
        levellist=np.arange(minlevel,maxlevel+dzlevel,dzlevel)
        farlevel=levellist[0]
        if abs(levellist)[0]<abs(levellist)[-1]:
            levellist=np.flipud(levellist)
            farlevel=levellist[0]
        if data_meant=='':
            #print('Be sure the data is an anomaly', end='')
            if sfilter=='none' or sfilter=='':
                dataanomaly = ma.masked_array(data[ii,:,:], mask)
            elif sfilter=='uniform':
                nofilterdata=data[ii,:,:]
                nofilterdata = nofilterdata - ndimage.uniform_filter(nofilterdata, size=70)
                dataanomaly = ma.masked_array(nofilterdata, mask)
            elif sfilter=='gaussian':
                nofilterdata=data[ii,:,:]
                nofilterdata = nofilterdata - ndimage.gaussian_filter(nofilterdata, sigma=20)
                dataanomaly = ma.masked_array(nofilterdata, mask)
        else:
            if sfilter=='none' or sfilter=='':
                dataanomaly=ma.masked_array(data[ii,:,:]-data_meant, mask)
            elif sfilter=='uniform':
                nofilterdata=data[ii,:,:]-data_meant
                nofilterdata = nofilterdata- ndimage.uniform_filter(nofilterdata, size=70)
                dataanomaly = ma.masked_array(nofilterdata, mask)
            elif sfilter=='gaussian':
                nofilterdata=data[ii,:,:]-data_meant
                nofilterdata =  nofilterdata - ndimage.gaussian_filter(nofilterdata, sigma=20)
                dataanomaly = ma.masked_array(nofilterdata, mask)
                
        for ll in levellist:
            if minlevel<0 and maxlevel<0:
                levels=[-500,ll]
            elif minlevel>0 and maxlevel>0:
                levels=[ll,500]
            #tic=time.time()
            eddies,check,numbereddies=scan_eddym(dataanomaly,x,y,levels,ii\
                          ,areamap,mask=mask,destdir=destdir\
                          ,physics=physics,eddycenter=eddycenter\
                          ,checkgauss=checkgauss,checkarea=checkarea\
                          ,eccenfit=eccenfit,ellipsrsquarefit=ellipsrsquarefit\
                          ,gaussrsquarefit=gaussrsquarefit,mode=mode\
                          ,diagnostics=diagnostics,plotdata=plotdata,pprint=pprint)
            #print('ellapse identification:',time.time()-tic)
            #print(eddies)
            if check==True and checkcount==0:
                eddzcheck=True
                checkcount=1
            else:
                eddzcheck=False
            #print('--------'+str(checkcount)+'---------')
            if eddies!=0 and check==True:
                if ll == farlevel or eddzcheck==True:
                    eddz = dict_eddyz(dataanomaly,x,y,ii,ll,farlevel,eddies,diagnostics=diagnostics)
                else:
                    #tic=time.time()
                    eddz = dict_eddyz(dataanomaly,x,y,ii,ll,farlevel,eddies,eddz,diagnostics=diagnostics)
                    #print('ellapse dz:',time.time()-tic)
                #print(eddies['EddyN'])
                #print(eddz['EddyN'])

        if ii==0:
            eddytd=dict_eddyt(ii,eddz)
        else:
            #tic=time.time()
            #print(eddz)
            eddytd=dict_eddyt(ii,eddz,eddytd,data=dataanomaly,x=x,y=y) 
            #print('ellapse dt:',time.time()-tic)
        #print(len(eddytd.keys()))
        numbereddieslevels=numbereddieslevels+numbereddies
        pp.timepercentprint(t0,t1,tstep,ii,numbereddieslevels)
    if destdir!='':
        if saveformat=='nc':
            eddync(destdir+str(level)+'.nc',eddytd)
        else:
            np.save(destdir+str(level)+'.npy',eddytd)
    return eddytd

def analyseddyt(data,x,y,level,t0,t1,tstep,data_meant='',areamap='',mask='',physics='',eddycenter='masscenter',eccenfit=0.95,gaussrsquarefit=0.5,ellipsrsquarefit=0.9,mode='gaussian',sfilter='none',checkgauss=True,checkarea=True,destdir='',saveformat='nc',diagnostics=False,plotdata=False,pprint=False):
    '''
    *************Analys eddy in t ***********
    Function to identify each eddy using closed contours, 
    moving in time and contour levels
    Usage:
    
    Example:

    Author: Josue Martinez Moreno, 2017
    '''
    eddytd=''
    if len(np.shape(data))<3:
        print('The data need to have 3d [i.e. data(t,x,y)]')
        #return
    if areamap=='':
        areamap=np.array([[0,len(x)],[0,len(y)]])
    if mask == '':
        if len(np.shape(data))<3:
            mask=ma.getmask(data[:,:])
        else:
            mask=ma.getmask(data[0,:,:])
    pp =  Printer(); 
    for ii in range(t0,t1,tstep):
        if data_meant=='':
            #print('Be sure the data is an anomaly', end='')
            if sfilter=='none' or sfilter=='':
                dataanomaly = ma.masked_array(data[ii,:,:], mask)
            elif sfilter=='uniform':
                nofilterdata=data[ii,:,:]-data_meant
                nofilterdata = nofilterdata - ndimage.uniform_filter(nofilterdata, size=40)
                dataanomaly = ma.masked_array(nofilterdata, mask)
            elif sfilter=='gaussian':
                nofilterdata=data[ii,:,:]-data_meant
                nofilterdata = nofilterdata - ndimage.gaussian_filter(nofilterdata, sigma=20)
                dataanomaly = ma.masked_array(nofilterdata, mask)
        else:
            if sfilter=='none' or sfilter=='':
                dataanomaly=ma.masked_array(data[ii,:,:]-data_meant, mask)
            elif sfilter=='uniform':
                nofilterdata=data[ii,:,:]-data_meant
                nofilterdata = nofilterdata- ndimage.uniform_filter(nofilterdata, size=40)
                dataanomaly = ma.masked_array(nofilterdata, mask)
            elif sfilter=='gaussian':
                nofilterdata=data[ii,:,:]-data_meant
                nofilterdata =  nofilterdata - ndimage.gaussian_filter(nofilterdata, sigma=20)
                dataanomaly = ma.masked_array(nofilterdata, mask)
        #del nofilterdata
        #Levels to Analyse, note that one of them is an extreme value,
        #This is because we don't want interference from any other contour.
        if level<0:
            levels=[-500,level]
        elif level>0:
            levels=[level,500]
        eddies,check,numbereddies=scan_eddym(dataanomaly,x,y,levels,ii,areamap,mask=mask,destdir=destdir\
                      ,physics=physics,eddycenter=eddycenter,checkgauss=checkgauss,checkarea=checkarea\
                      ,eccenfit=eccenfit,ellipsrsquarefit=ellipsrsquarefit\
                      ,gaussrsquarefit=gaussrsquarefit,mode=mode\
                      ,diagnostics=diagnostics,plotdata=plotdata,pprint=pprint)
        if eddies!=0 and check==True:
            if ii==0:
                eddytd=dict_eddyt(ii,eddies)
            else:
                eddytd=dict_eddyt(ii,eddies,eddytd) 
        pp.timepercentprint(t0,t1,tstep,ii,numbereddies)
    if destdir!='':
        if saveformat=='nc':
            eddync(destdir+str(level)+'.nc',eddytd)
        else:
            np.save(destdir+str(level)+'.npy',eddytd)
    return eddytd


def trackmatix(eddydict):
    eddy=0
    time=0
    for key,value in eddydict.items():
        if type(value['time'])!=int:
            if value['time'][-1]>time:
                time=value['time'][-1]+1

    positions=np.zeros([2,len(eddydict.items()),int(time)])
    for key,value in eddydict.items():
        if type(value['time'])==int:
            positions[0,eddy,value['time']]=value['position'][0]
            positions[1,eddy,value['time']]=value['position'][1]
        else:
            realinx=0
            for ii in value['time']:
                #print(ii)
                positions[0,eddy,ii]=squeeze(value['position'][realinx,0])
                positions[1,eddy,ii]=squeeze(value['position'][realinx,1])
                realinx=realinx+1
        eddy=eddy+1
    positions[positions==0]=np.nan
    return(positions)