        function femmesh=loadfemmesh_h5(h5file,iplot,ilabel,ifig)
            if~exist('h5file','var');h5file='femmesh.h5';end
            if~exist('iplot','var');iplot=0;end
            if~exist('ilabel','var');ilabel=0;end

            disp(['----loadhdf5 from ',h5file,'----']);

            femmesh.nvert=h5read(h5file,'/femmesh/nvert');
            
            femmesh.ntria=h5read(h5file,'/femmesh/ntria');
            
            femmesh.nvert_in=h5read(h5file,'/femmesh/nvert_in');
            
            femmesh.nvert_ex=h5read(h5file,'/femmesh/nvert_ex');
            
            %--note in fortran, vert size is (2,nvert)but in matlab it is (nvert,2)!!!
            femmesh.vert=h5read(h5file,'/femmesh/vert').';
            
            femmesh.idxivert=h5read(h5file,'/femmesh/idxivert');
            
            femmesh.idxevert=h5read(h5file,'/femmesh/idxevert');
            
            femmesh.tria=h5read(h5file,'/femmesh/tria').';

        try
            femmesh.nbcRZ=h5read(h5file,'/femmesh/nbcRZ');
            
            femmesh.Rbc=h5read(h5file,'/femmesh/Rbc');
            
            femmesh.Zbc=h5read(h5file,'/femmesh/Zbc');
        catch
                warning('--warning no nbcRZ,Rbc,Zbc')
        end

            %h5disp(h5file)

  if iplot==1 
      if~exist('ifig','var')
        ifig=figure('Units','normalized','Position',[.05,.05,.32,.6],'color','w');
      else
          figure(ifig);
      end
      %figure('position',[100 100 500 400])
        patch('faces',femmesh.tria(:,1:3),'vertices',femmesh.vert,'facecolor','none','edgecolor',[.2,.2,.2]) ;
        hold on; 
        %axis image off;
        if ilabel==1
            text(femmesh.vert(:,1),femmesh.vert(:,2),num2str((1:femmesh.nvert)'))
            Rtri=(femmesh.vert(femmesh.tria(:,1),1)+femmesh.vert(femmesh.tria(:,2),1)+femmesh.vert(femmesh.tria(:,3),1))/3;
            Ztri=(femmesh.vert(femmesh.tria(:,1),2)+femmesh.vert(femmesh.tria(:,2),2)+femmesh.vert(femmesh.tria(:,3),2))/3;

            text(Rtri,Ztri,num2str((1:femmesh.ntria)'),'color','r')
        end
        axis equal
  end
        end %loadfemmesh2h5
