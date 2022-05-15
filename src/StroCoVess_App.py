import os
import sys
import subprocess
import pathlib
from pathlib import Path
import csv
import numpy as np

import tkinter as tk
import tkinter.filedialog
import tkinter.messagebox
from tkinter.ttk import Progressbar

import webbrowser

import itk
from itk import TubeTK as tube

def is_bundled():
    return getattr(sys, 'frozen', False) and hasattr(sys, '_MEIPASS')

def get_lib_path():
    if is_bundled():
        return os.path.join(sys._MEIPASS, 'StroCoVess')
    return os.path.dirname(os.path.realpath(__file__))+'/../lib'

def get_bin_path():
    if is_bundled():
        return os.path.join(sys._MEIPASS, 'StroCoVess', 'bin')
    return os.path.dirname(os.path.realpath(__file__))+'/bin'

def get_atlas_path():
    if is_bundled():
        return os.path.join(sys._MEIPASS, 'StroCoVess', 'atlas')
    return os.path.dirname(os.path.realpath(__file__))+'/atlas'


sys.path.append(get_lib_path())
from StroCoVess_Lib import *
from ToggleFrame import *

class CTP_App(tk.Tk):

    def __init__(self):
        super().__init__()

        self.ctp_files = ["../data/CTP/CTP04.mha",
                          "../data/CTP/CTP06.mha",
                          "../data/CTP/CTP08.mha",
                          "../data/CTP/CTP10.mha",
                          "../data/CTP/CTP12.mha",
                          "../data/CTP/CTP14.mha",
                          "../data/CTP/CTP16.mha",
                          "../data/CTP/CTP18.mha",
                          "../data/CTP/CTP20.mha",
                          "../data/CTP/CTP22.mha",
                          "../data/CTP/CTP24.mha",
                          "../data/CTP/CTP26.mha",
                          "../data/CTP/CTP28.mha",
                          "../data/CTP/CTP30.mha",
                          "../data/CTP/CTP32.mha"]

        self.ct_file = ""
        self.cta_file = ""
        self.dsa_file = ""

        self.cbf_file = "../data/CTP-PerfusionMaps/CBF.nii"
        self.cbv_file = "../data/CTP-PerfusionMaps/CBV.nii"
        self.tmax_file = "../data/CTP-PerfusionMaps/Tmax.nii"
        self.ttp_file = "../data/CTP-PerfusionMaps/TTP.nii"

        self.dcm_in_dir = "./"
        self.dcm_out_dir = "./"

        self.prep_3d_in_files = self.ctp_files
        self.prep_3d_out_dir = "./"

        self.prep_4d_in_file = "../data/CTP/CTP_4D.mha"
        self.prep_4d_out_dir = "../data/results"

        self.workflow_4d_in_file = "../data/CTP/CTP_4D.mha"
        self.workflow_4d_out_dir = "../data/results"

        self.workflow_3d_in_file = self.ctp_files
        self.workflow_3d_out_dir = "../data/results"

        self.process_out_dir = "../data/results"

        self.progress_status = ""

        self.title("SCV App")

        frm_title = tk.Frame(master=self)
        lbl_title = tk.Label(master=frm_title,
            text="Stroke Collateral Vessels",
            font=('Helvetica', 16, 'bold')
            ).pack(pady=5)
        self.debug = tk.IntVar()
        ckb_debug = tk.Checkbutton(master=frm_title,
            text="Debug",
            variable=self.debug,
            pady=5).pack()
        frm_title.pack(fill=tk.BOTH)
    
        frm_utility = tk.Frame(master=self,
            relief=tk.RIDGE,
            borderwidth=5,
            bg="light yellow",
            pady=5)
        lbl_utility = tk.Label(master=frm_utility,
            text="Utility Functions",
            bg="light yellow").pack()
        btn_dcm = tk.Button(master=frm_utility,
            text="Convert DICOM files",
            command=self.hdl_dcm,
            width=20
            ).pack(pady=5)
        btn_view = tk.Button(master=frm_utility,
            text="View a file",
            command=self.hdl_view,
            width=20
            ).pack(pady=5)
        btn_help = tk.Button(master=frm_utility,
            text="Help",
            command=self.hdl_help,
            width=20
            ).pack(pady=5)
        frm_utility.pack(fill=tk.X)
    
        frm_workflows = tk.Frame(master=self,
            relief=tk.RIDGE,
            borderwidth=5,
            bg="light green",
            pady=5)
        lbl_workflows = tk.Label(master=frm_workflows,
            text="Process Perfusion files",
            bg="light green").pack()

        btn_workflow_4d = tk.Button(master=frm_workflows,
            text="Process 4D perfusion file",
            command=self.hdl_workflow_4d,
            width=20
            ).pack(pady=5)
        btn_workflow_3d = tk.Button(master=frm_workflows,
            text="Process 3D perfusion file",
            command=self.hdl_workflow_3d,
            width=20
            ).pack(pady=5)
        frm_workflows.pack(fill=tk.X)

        frm_steps = ToggledFrame(master=self,
            relief=tk.RIDGE,
            text="Advanced Options",
            borderwidth=5,
            bg="light sky blue",
            pady=5)
        frm_steps.pack(fill=tk.X) 
        lbl_steps = tk.Label(master=frm_steps.sub_frame,
            text="Workflow methods",
            bg="light sky blue").pack()

        frm_prep = tk.Frame(master=frm_steps.sub_frame,
            relief=tk.GROOVE,
            borderwidth=5,
            bg="light sky blue",
            padx=5,
            pady=5)
        lbl_prep= tk.Label(master=frm_prep,
            text="Step 0: Preprocess:",
            bg="light sky blue"
            ).pack(side=tk.LEFT)
        btn_prep_4d = tk.Button(master=frm_prep,
            text="Prepare 4D CTP file",
            command=self.hdl_prep_4d,
            width=20
            ).pack(pady=5)
        btn_prep_3d= tk.Button(master=frm_prep,
            text="Prepare 3D CTP files",
            command=self.hdl_prep_3d,
            width=20
            ).pack(pady=5)
        frm_prep.pack(padx=5,fill=tk.X)

        frm_ctp = tk.Frame(master=frm_steps.sub_frame,
            relief=tk.GROOVE,
            borderwidth=5,
            bg="light sky blue",
            padx=5,
            pady=5)
        lbl_ctp= tk.Label(master=frm_ctp,
            text="Step 1: Select one:",
            bg="light sky blue"
            ).pack(side=tk.LEFT)
        btn_ctp= tk.Button(master=frm_ctp,
            text="Set CTP files",
            command=self.hdl_ctp,
            width=20).pack()
        btn_cta= tk.Button(master=frm_ctp,
            text="Set CTA file",
            command=self.hdl_cta,
            width=20).pack()
        frm_ctp.pack(padx=5,fill=tk.X)
    
        frm_perf = tk.Frame(master=frm_steps.sub_frame,
            relief=tk.GROOVE,
            borderwidth=5,
            bg="light sky blue",
            padx=5,
            pady=5)
        lbl_perf = tk.Label(master=frm_perf,
            text="Step 2: Optionally select any:",
            bg="light sky blue"
            ).pack(side=tk.LEFT)
        btn_cbf= tk.Button(master=frm_perf,
            text="Set CBF file",
            command=self.hdl_cbf,
            width=20).pack()
        btn_cbv= tk.Button(master=frm_perf,
            text="Set CBV file",
            command=self.hdl_cbv,
            width=20).pack()
        btn_tmax= tk.Button(master=frm_perf,
            text="Set Tmax file",
            command=self.hdl_tmax,
            width=20).pack()
        btn_ttp= tk.Button(master=frm_perf,
            text="Set TTP file",
            command=self.hdl_ttp,
            width=20).pack()
        frm_perf.pack(padx=5,fill=tk.X)
    
        frm_process = tk.Frame(master=frm_steps.sub_frame,
            relief=tk.GROOVE,
            borderwidth=5,
            bg="light sky blue",
            padx=5,
            pady=5)
        lbl_process = tk.Label(master=frm_process,
            text="Step 3: Process:",
            bg="light sky blue",
            ).pack(side=tk.LEFT)
        btn_process_out_dir = tk.Button(master=frm_process,
            text="Set output directory",
            command=self.hdl_process_out_dir,
            width=20
            ).pack(pady=5)
        btn_process = tk.Button(master=frm_process,
            text="Process",
            command=self.hdl_process,
            bg="pale green",
            width=20
            ).pack(pady=5)
        frm_process.pack(padx=5,fill=tk.BOTH)

        #frm_steps.pack(fill=tk.BOTH)

        frm_progress = tk.Frame(master=self,
            relief=tk.RIDGE,
            borderwidth=5,
            bg="light blue",
            pady=5)
        lbl_progress = tk.Label(master=frm_progress,
            text="Progress",
            bg="light blue").pack()

        self.lbl_progress = tk.Label(frm_progress,
            text="Status: Idle",
            bg="light blue",
            width=40)
        self.lbl_progress.pack()

        self.pgb_progress = Progressbar(frm_progress,
            orient=tk.HORIZONTAL,
            length=150,
            mode='determinate')
        self.pgb_progress.pack()
        self.pgb_subprogress = Progressbar(frm_progress,
            orient=tk.HORIZONTAL,
            length=150,
            mode='determinate')
        self.pgb_subprogress.pack()
        frm_progress.pack(fill=tk.BOTH)
    

#################################
#################################
#################################
    def hdl_help(self):
        box_help = tk.messagebox.showinfo(title="Help",
            message = "      Stoke Collateral Vessels \n" +
            "Kitware, Inc. and The University of North Carolina \n" +
            "\n" +
            "Use this program to generate vessel-augmented \n" +
            "perfusion research reports for patients with stroke. \n" +
            "\n" +
            "This program is distributed \"AS-IS\" and is not \n" +
            "suitable for any expressed or implied purpose. In \n" +
            "particular, it should never be used for clinical \n" +
            "decision making. \n" +
            "\n" +
            "DICOM conversion provided by dcm2niix. \n" +
            "\n" +
            "Learn more at \n" +
            "   http://github.com/KitwareMedical/ \n" +
            "      ITKTubeTK-StrokeCollateralVessels"
            )

#################################
#################################
#################################
    def hdl_dcm(self):
        win_dcm = tk.Tk()

        frm_title = tk.Frame(master=win_dcm)
        lbl_title = tk.Label(master=frm_title,
            text="DICOM Conversion",
            pady=5).pack(padx=5,pady=5)
        frm_title.pack(fill=tk.BOTH)

        btn_dcm_in_dir = tk.Button(master=win_dcm,
            text="1) Set input directory",
            command=self.hdl_dcm_in_dir,
            width=20).pack(padx=5,pady=5)
        btn_dcm_out_dir = tk.Button(master=win_dcm,
            text="2) Set output directory",
            command=self.hdl_dcm_out_dir,
            width=20).pack(padx=5,pady=5)
        btn_dcm_process = tk.Button(master=win_dcm,
            text="3) Process",
            command=self.hdl_dcm_process,
            bg="pale green",
            width=20).pack(padx=5,pady=5)

        win_dcm.mainloop()

    def hdl_dcm_in_dir(self):
        self.dcm_in_dir = os.path.realpath(tk.filedialog.askdirectory(
            title='Dicom input directory',
            initialdir=self.dcm_in_dir))

    def hdl_dcm_out_dir(self):
        self.dcm_out_dir = os.path.realpath(tk.filedialog.askdirectory(
            title='Output directory',
            initialdir=self.dcm_out_dir))

    def hdl_dcm_process(self):
        dcm2niix = os.path.realpath( os.path.join(get_bin_path(),
            'dcm2niix.exe') )
        subprocess.call([dcm2niix, "-o", self.dcm_out_dir, self.dcm_in_dir])


#################################
#################################
#################################
    def hdl_workflow_4d(self):
        win_workflow_4d = tk.Tk()

        frm_title = tk.Frame(master=win_workflow_4d)
        lbl_title = tk.Label(master=frm_title,
            text="Prepare 4D CTP for perfusion toolbox",
            pady=5).pack(padx=5,pady=5)
        frm_title.pack(fill=tk.BOTH)

        btn_workflow_4d_in_file = tk.Button(master=win_workflow_4d,
            text="1) Set input CTP file",
            command=self.hdl_workflow_4d_in_file,
            width=20).pack(padx=5,pady=5)
        btn_workflow_4d_out_dir = tk.Button(master=win_workflow_4d,
            text="2) Set output directory",
            command=self.hdl_workflow_4d_out_dir,
            width=20).pack(padx=5,pady=5)
        btn_workflow_4d_process = tk.Button(master=win_workflow_4d,
            text="3) Process",
            command=self.hdl_workflow_4d_process,
            bg="pale green",
            width=20).pack(padx=5,pady=5)

        win_workflow_4d.mainloop()

    def hdl_workflow_4d_in_file(self):
        filepath,filename = os.path.split(self.workflow_4d_in_file)
        self.workflow_4d_in_file = tk.filedialog.askopenfilename(
            title='4D CTP file to be prepared',
            initialdir=filepath,
            initialfile=filename)

    def hdl_workflow_4d_out_dir(self):
        self.workflow_4d_out_dir = os.path.realpath(
            tk.filedialog.askdirectory(
            title='Output directory',
            initialdir=self.workflow_4d_out_dir))

    def hdl_workflow_4d_process(self):
        self.report_progress("Generating 4D CTP report",5)
        debug = False
        if self.debug.get() == 1:
            debug = True

        self.atlas_path = get_atlas_path()
        scv_generate_4d_ctp_vessel_report( self.workflow_4d_in_file,
            self.atlas_path,self.workflow_4d_out_dir,self.report_progress,
            self.report_subprogress,debug)

#################################
#################################
#################################
    def hdl_workflow_3d(self):
        win_workflow_3d = tk.Tk()

        frm_title = tk.Frame(master=win_workflow_3d)
        lbl_title = tk.Label(master=frm_title,
            text="Prepare 4D CTP for perfusion toolbox",
            pady=5).pack(padx=5,pady=5)
        frm_title.pack(fill=tk.BOTH)

        btn_workflow_3d_in_files = tk.Button(master=win_workflow_3d,
            text="1) Set input CTP files",
            command=self.hdl_workflow_3d_in_files,
            width=20).pack(padx=5,pady=5)
        btn_workflow_3d_out_dir = tk.Button(master=win_workflow_3d,
            text="2) Set output directory",
            command=self.hdl_workflow_3d_out_dir,
            width=20).pack(padx=5,pady=5)
        btn_workflow_3d_process = tk.Button(master=win_workflow_3d,
            text="3) Process",
            command=self.hdl_workflow_3d_process,
            bg="pale green",
            width=20).pack(padx=5,pady=5)

        win_workflow_3d.mainloop()

    def hdl_workflow_3d_in_files(self):
        if len(self.workflow_3d_in_files) > 0:
            filepath,filename = os.path.split(self.workflow_3d_in_files[0])
            self.workflow_3d_in_files = tk.filedialog.askopenfilename(
                title='3D CTP files to be prepared',
                initialdir=filepath,
                initialfile=filename)
        else:
            self.workflow_3d_in_files = tk.filedialog.askopenfilename(
                title='3D CTP files to be prepared')

    def hdl_workflow_3d_out_dir(self):
        self.workflow_3d_out_dir = os.path.realpath(
            tk.filedialog.askdirectory(
            title='Output directory',
            initialdir=self.workflow_3d_out_dir))

    def hdl_workflow_3d_process(self):
        self.report_progress("Generating 3D CTP report",5)
        debug = False
        if self.debug.get() == 1:
            debug = True

        self.atlas_path = get_atlas_path()
        scv_generate_3d_ctp_vessel_report( self.workflow_3d_in_files,
            self.atlas_path,self.workflow_3d_out_dir, report_progress,
            report_subprogress, debug)


#################################
#################################
#################################
    def hdl_prep_3d(self):
        win_prep_3d = tk.Tk()

        frm_title = tk.Frame(master=win_prep_3d)
        lbl_title = tk.Label(master=frm_title,
            text="Image Registration",
            pady=5).pack(padx=5,pady=5)
        frm_title.pack(fill=tk.BOTH)

        btn_prep_3d_in_files = tk.Button(master=win_prep_3d,
            text="1) Set input files",
            command=self.hdl_prep_3d_in_files,
            width=20).pack(padx=5,pady=5)
        btn_prep_3d_out_dir = tk.Button(master=win_prep_3d,
            text="2) Set output directory",
            command=self.hdl_prep_3d_out_dir,
            width=20).pack(padx=5,pady=5)
        btn_prep_3d_process = tk.Button(master=win_prep_3d,
            text="3) Process",
            command=self.hdl_prep_3d_process,
            bg="pale green",
            width=20).pack(padx=5,pady=5)

        win_prep_3d.mainloop()

    def hdl_prep_3d_in_files(self):
        filepath,filename = os.path.split(self.prep_3d_in_files[0])
        self.prep_3d_in_files = tk.filedialog.askopenfilenames(
            title='Input (moving) image files to be registered',
            initialdir=filepath)

    def hdl_prep_3d_out_dir(self):
        self.prep_3d_out_dir = os.path.realpath(tk.filedialog.askdirectory(
            title='Output directory',
            initialdir=self.prep_3d_out_dir))

    def hdl_prep_3d_process(self):
        self.report_progress("Registering images",5)
        debug = False
        if self.debug.get() == 1:
            debug = True

        scv_prepare_3d_for_perfusion_toolbox(self.prep_3d_in_files,
            self.prep_3d_out_dir, self.report_progress,
            self.report_subprogress, debug)

#################################
#################################
#################################
    def hdl_prep_4d(self):
        win_prep_4d = tk.Tk()

        frm_title = tk.Frame(master=win_prep_4d)
        lbl_title = tk.Label(master=frm_title,
            text="Prepare 4D CTP for perfusion toolbox",
            pady=5).pack(padx=5,pady=5)
        frm_title.pack(fill=tk.BOTH)

        btn_prep_4d_in_file = tk.Button(master=win_prep_4d,
            text="1) Set input file",
            command=self.hdl_prep_4d_in_file,
            width=20).pack(padx=5,pady=5)
        btn_prep_4d_out_dir = tk.Button(master=win_prep_4d,
            text="2) Set output directory",
            command=self.hdl_prep_4d_out_dir,
            width=20).pack(padx=5,pady=5)
        btn_prep_4d_process = tk.Button(master=win_prep_4d,
            text="3) Process",
            command=self.hdl_prep_4d_process,
            bg="pale green",
            width=20).pack(padx=5,pady=5)

        win_prep_4d.mainloop()

    def hdl_prep_4d_in_file(self):
        filepath,filename = os.path.split(self.prep_4d_in_file)
        self.prep_4d_in_file = tk.filedialog.askopenfilename(
            title='4D CTP file to be prepared',
            initialdir=filepath,
            initialfile=filename)

    def hdl_prep_4d_out_dir(self):
        self.prep_4d_out_dir = os.path.realpath(
            tk.filedialog.askdirectory(
            title='Output directory',
            initialdir=self.prep_4d_out_dir))

    def hdl_prep_4d_process(self):
        self.report_progress("Preparing 4D CTP image",5)
        debug = False
        if self.debug.get() == 1:
            debug = True

        scv_prepare_4d_for_perfusion_toolbox(self.prep_4d_in_file,
            self.prep_4d_out_dir, self.report_progress,
            self.report_subprogress, debug)

#################################
#################################
#################################
    def hdl_view(self):
        #view_file = os.path.realpath(tk.filedialog.askopenfilename())
        #uri = pathlib.Path(view_file).as_uri()
        #path,name = os.path.split(view_file)
        url = "https://kitware.github.io/paraview-glance/app/"
        #url += "?name=" + name
        #url += "&url=" + uri
        #print(url)
        webbrowser.open(url)
    
#################################
#################################
#################################
    def hdl_ctp(self):
        initialdir = None
        if len(self.ctp_files)>0:
            initialdir = os.path.dirname(self.ctp_files[0])
        self.ctp_files = list(tk.filedialog.askopenfilenames(
            title='CTP files',
            initialdir=initialdir))
        self.cta_file = ""

    def hdl_cta(self):
        initialdir = None
        initialfile = None
        if len(self.cta_file)>0:
            initialdir,initialfile = os.path.split(self.cta_file)
        self.cta_file = os.path.realpath(tk.filedialog.askopenfilename(
            title='CTA file',
            initialdir=initialdir,
            initialfile=initialfile))
        self.ctp_files = []

    def hdl_cbf(self):
        initialdir = None
        initialfile = None
        if len(self.cbf_file)>0:
            initialdir,initialfile = os.path.split(self.cbf_file)
        self.cbf_file = os.path.realpath(tk.filedialog.askopenfilename(
            title='CBF file',
            initialdir=initialdir,
            initialfile=initialfile))

    def hdl_cbv(self):
        initialdir = None
        initialfile = None
        if len(self.cbv_file)>0:
            initialdir,initialfile = os.path.split(self.cbv_file)
        self.cbv_file = os.path.realpath(tk.filedialog.askopenfilename(
            title='CBV file',
            initialdir=initialdir,
            initialfile=initialfile))

    def hdl_tmax(self):
        initialdir = None
        initialfile = None
        if len(self.tmax_file)>0:
            initialdir,initialfile = os.path.split(self.tmax_file)
        self.tmax_file = os.path.realpath(tk.filedialog.askopenfilename(
            title='TMax file',
            initialdir=initialdir,
            initialfile=initialfile))

    def hdl_ttp(self):
        initialdir = None
        initialfile = None
        if len(self.ttp_file)>0:
            initialdir,initialfile = os.path.split(self.ttp_file)
        self.ttp_file = os.path.realpath(tk.filedialog.askopenfilename(
            title='TTP file',
            initialdir=initialdir,
            initialfile=initialfile))

    def hdl_process_out_dir(self):
        initialdir = None
        if len(self.process_out_dir)>0:
            initialdir = self.process_out_dir
        self.process_out_dir = os.path.realpath(tk.filedialog.askdirectory(
            title='Output directory',
            initialdir=initialdir))

#################################
#################################
#################################
    def report_progress(self, label, percentage):
        self.progress_status = label
        print(label)
        self.lbl_progress['text'] = label
        self.pgb_progress['value'] = percentage
        self.pgb_subprogress['value'] = 0
        self.update()

    def report_subprogress(self, label, percentage):
        progress_label = self.progress_status+": "+label
        self.lbl_progress['text'] = progress_label
        print(progress_label)
        self.pgb_subprogress['value'] = percentage
        self.update()

#################################
#################################
#################################
    def hdl_process(self):
        if not os.path.exists(self.process_out_dir):
            os.mkdir(self.process_out_dir)

        debug = False
        if self.debug.get() == 1:
            debug = True

        # User must supply either CTA or CTP data
        # They can also provide DSA data, but it must have had
        #    the brain extracted already.
        cta_im = None
        dsa_im = None
        if len(self.ctp_files)>0:
            self.report_progress("Converting CTP to CTA",5)
            ct_im,cta_im,dsa_im = scv_convert_ctp_to_cta(self.ctp_files,
                report_progress = self.report_subprogress,
                debug=debug,
                output_dir=self.process_out_dir)
            self.report_progress("Converting CTP to CTA",10)
            itk.imwrite(ct_im,os.path.join(self.process_out_dir,"ct.mha"),
                compression=True)
            itk.imwrite(cta_im,os.path.join(self.process_out_dir,"cta.mha"),
                compression=True)
            itk.imwrite(dsa_im,os.path.join(self.process_out_dir,"dsa.mha"),
                compression=True)
        elif len(self.cta_file)>0:
            self.report_progress("Reading CTA",5)
            cta_im = itk.imread(self.cta_file, itk.F)
            self.report_progress("Reading CTA",10)
        elif len(self.dsa_file)>0:
            self.report_progress("Reading DSA",5)
            dsa_im = itk.imread(self.dsa_file,itk.F)
            self.report_progress("Reading DSA",10)
        else:
            self.report_progress("ERROR",100)
            tk.messagebox.showerror(title="Error",
                message="Must set CTP files or CTA file.")
            return

        if dsa_im==None and len(self.dsa_file)>0:
            self.report_progress("Reading DSA",5)
            dsa_im = itk.imread(self.dsa_file,itk.F)
            self.report_progress("Reading DSA",10)

        self.report_progress("Segmenting Brain",20)
        if cta_im != None:
            cta_brain_im,mask_brain = scv_segment_brain_from_ct(cta_im,
                report_progress = self.report_subprogress,
                debug=debug)
            itk.imwrite(cta_brain_im,
                os.path.join(self.process_out_dir,"cta_brain.mha"),
                compression=True)
            # Use CTA brain to mask DSA and create DSA_Brain image
            if dsa_im != None:
                ImageMath = tube.ImageMath.New(Input=dsa_im)
                ImageMath.ReplaceValuesOutsideMaskRange(cta_brain_im,
                    0.000001,9999,0)
                dsa_brain_im = ImageMath.GetOutput()
                itk.imwrite(dsa_brain_im,
                    os.path.join(self.process_out_dir,"dsa_brain.mha"),
                    compression=True)
        else:
            # If it is required and a CTA wasn't provided
            #   or CTA wasn't generated from CTP, then throw and error
            self.report_progress("ERROR",100)
            tk.messagebox.showerror(title="Error",
                message="Cannot perform brain segmentation using DSA.\n" +
                        "Please also include CTP or CTA data.")
            return

        in_im = cta_im
        in_brain_im = cta_brain_im
        in_name = "cta"
        # If DSA is available, use it instead of CTA
        if dsa_im != None:
            in_im = dsa_im
            in_brain_im = dsa_brain_im
            in_name = "dsa"

        self.report_progress("Enhancing vessels",40)
        # Enhancing vessels creates an image in which intensity is
        #    related to "vesselness" instead of being related to the
        #    amount of contrast agent in the vessel.  This simplifies
        #    subsequent vessel seeding and traversal stopping criteria.
        in_vess_im,in_brain_vess_im = scv_enhance_vessels_in_cta(
            in_im,
            in_brain_im,
            report_progress=self.report_subprogress,
            debug=debug)
        itk.imwrite(in_vess_im,
            os.path.join(self.process_out_dir,
                in_name+"_vessels_enhanced.mha"),
            compression=True)
        itk.imwrite(in_brain_vess_im,
            os.path.join(self.process_out_dir,
                in_name+"_brain_vessels_enhanced.mha"),
            compression=True)

        self.report_progress("Extracting vessels",60)
        vess_mask_im,vess_so = scv_extract_vessels_from_cta(
            in_vess_im,
            in_brain_vess_im,
            report_progress=self.report_subprogress,
            debug=debug,
            output_dir=self.process_out_dir)

        itk.imwrite(in_brain_vess_im,
            os.path.join(self.process_out_dir,
                in_name+"_vessels_extracted.mha"),
            compression=True)

        SOWriter = itk.SpatialObjectWriter[3].New()
        SOWriter.SetInput(vess_so)
        SOWriter.SetBinaryPoints(True)
        SOWriter.SetFileName(os.path.join(self.process_out_dir,
            in_name+"_vessels_extracted.tre"))
        SOWriter.Update()

        VTPWriter = itk.WriteTubesAsPolyData.New()
        VTPWriter.SetInput(vess_so)
        VTPWriter.SetFileName(os.path.join(self.process_out_dir,
            in_name+"_vessels_extracted.vtp"))
        VTPWriter.Update()
        
        self.report_progress("Generating Perfusion Stats",80)

        script_dir = os.path.dirname(os.path.realpath(__file__))
        self.atlas_path = get_atlas_path()
        atlas_im = itk.imread(
            os.path.join(self.atlas_path,'atlas_brainweb.mha'),
            itk.F)
        atlas_mask_im = itk.imread(
            os.path.join(self.atlas_path,'atlas_brainweb_mask.mha'),
            itk.F)
        atlas_reg_im,atlas_mask_reg_im = scv_register_atlas_to_image(
            atlas_im,
            atlas_mask_im,
            in_brain_im)
        ImageMath = tube.ImageMath.New(Input=atlas_mask_reg_im)
        ImageMath.ReplaceValuesOutsideMaskRange(vess_mask_im,
            0.000001,9999,4)
        ImageMath.ReplaceValuesOutsideMaskRange(cta_brain_im,
            0.000001,9999,0)
        vess_atlas_mask_im = ImageMath.GetOutput()
        itk.imwrite(vess_atlas_mask_im,
            os.path.join(self.process_out_dir,
                in_name+"_vess_atlas_mask.mha"),
            compression=True)

        TubeMath = tube.TubeMath[3,itk.F].New()
        TubeMath.SetInputTubeGroup(vess_so)
        TubeMath.SetUseAllTubes()
        TubeMath.ComputeTubeRegions(vess_atlas_mask_im)

        graph_label = None
        graph_data = None
        ttp_im = None
        if len(self.ttp_file) > 0:
            self.report_progress("Generating TTP Graphs",92)
            ttp_im = itk.imread(self.ttp_file, itk.F)
            Resample = tube.ResampleImage.New(Input=ttp_im)
            Resample.SetMatchImage(vess_atlas_mask_im)
            Resample.Update()
            ttp_im = Resample.GetOutput()
            TubeMath.SetPointValuesFromImage(ttp_im, "TTP")
            TubeMath.SetPointValuesFromTubeRegions(ttp_im,
                "TTP_Tissue",
                1.5,
                4)
            time_bin,ttp_bin,ttp_count = scv_compute_atlas_region_stats(
                vess_atlas_mask_im,
                ttp_im,
                ttp_im,
                100,
                self.report_subprogress)
            graph_label = ["Bin_Num"]
            graph_data = np.arange(len(time_bin))
            graph_label = np.append(graph_label,"TPP")
            graph_data = np.stack((graph_data,time_bin))
            for r in range(1,ttp_bin.shape[0]):
                graph_label = np.append(graph_label,
                    "Count_Region_"+str(r))
                graph_data = np.concatenate((graph_data,
                    [ttp_count[r,:]]))
            print(graph_label.shape)
            print(graph_data.shape)


        if len(self.cbf_file) > 0:
            self.report_progress("Generating CBF Graphs",94)
            cbf_im = itk.imread(self.cbf_file, itk.F)
            Resample = tube.ResampleImage.New(Input=cbf_im)
            Resample.SetMatchImage(vess_atlas_mask_im)
            Resample.Update()
            cbf_im = Resample.GetOutput()
            TubeMath.SetPointValuesFromImage(cbf_im, "CBF")
            TubeMath.SetPointValuesFromTubeRegions(cbf_im,
                "CBF_Tissue",
                1.5,
                4)
            if ttp_im!=None:
                time_bin,cbf_bin,cbf_count = scv_compute_atlas_region_stats(
                    vess_atlas_mask_im,
                    ttp_im,
                    cbf_im,
                    100,
                    self.report_subprogress)
                for r in range(1,cbf_bin.shape[0]):
                    graph_label = np.append(graph_label,
                        "CBF_Region"+str(r))
                    graph_data = np.concatenate((graph_data,
                        [cbf_bin[r,:]]))

        if len(self.cbv_file) > 0:
            self.report_progress("Generating CBV Graphs",96)
            cbv_im = itk.imread(self.cbv_file, itk.F)
            Resample = tube.ResampleImage.New(Input=cbv_im)
            Resample.SetMatchImage(vess_atlas_mask_im)
            Resample.Update()
            cbv_im = Resample.GetOutput()
            TubeMath.SetPointValuesFromImage(cbv_im, "CBV")
            TubeMath.SetPointValuesFromTubeRegions(cbv_im,
                "CBV_Tissue",
                1.5,
                4)
            if ttp_im!=None:
                time_bin,cbv_bin,cbv_count = scv_compute_atlas_region_stats(
                    vess_atlas_mask_im,
                    ttp_im,
                    cbv_im,
                    100,
                    self.report_subprogress)
                for r in range(1,cbv_bin.shape[0]):
                    graph_label = np.append(graph_label,
                        "CBV_Region"+str(r))
                    graph_data = np.concatenate((graph_data,
                        [cbv_bin[r,:]]))
        if len(self.tmax_file) > 0:
            self.report_progress("Generating TMax Graphs",98)
            tmax_im = itk.imread(self.tmax_file, itk.F)
            Resample = tube.ResampleImage.New(Input=tmax_im)
            Resample.SetMatchImage(vess_atlas_mask_im)
            Resample.Update()
            tmax_im = Resample.GetOutput()
            TubeMath.SetPointValuesFromImage(tmax_im, "TMax")
            TubeMath.SetPointValuesFromTubeRegions(tmax_im,
                "TMax_Tissue",
                1.5,
                4)
            if ttp_im!=None:
                time_bin,tmax_bin,tmax_count = scv_compute_atlas_region_stats(
                    vess_atlas_mask_im,
                    ttp_im,
                    tmax_im,
                    100,
                    self.report_subprogress)
                for r in range(1,tmax_bin.shape[0]):
                    graph_label = np.append(graph_label,
                        "TMax_Region"+str(r))
                    graph_data = np.concatenate((graph_data,
                        [tmax_bin[r,:]]))

        self.report_progress("Saving results",99)
        SOWriter = itk.SpatialObjectWriter[3].New()
        SOWriter.SetInput(vess_so)
        SOWriter.SetBinaryPoints(True)
        SOWriter.SetFileName(os.path.join(self.process_out_dir,
            in_name+"_vessels_extracted_perf.tre"))
        SOWriter.Update()

        VTPWriter = itk.WriteTubesAsPolyData.New()
        VTPWriter.SetInput(vess_so)
        VTPWriter.SetFileName(os.path.join(self.process_out_dir,
            in_name+"_vessels_extracted_perf.vtp"))
        VTPWriter.Update()

        csvfilename = os.path.join(self.process_out_dir,
            in_name+"_vessels_extracted_perf.csv")
        csvfile = open(csvfilename,'w',newline='')
        csvwriter = csv.writer(csvfile,
            dialect='excel',
            quoting=csv.QUOTE_NONE)
        csvwriter.writerow(graph_label)
        for r in range(graph_data.shape[1]):
            csvwriter.writerow(['{:f}'.format(x) for x in graph_data[:,r]])
        csvfile.close()

        self.report_progress("Done!",100)
    
#################################
#################################
#################################
if __name__ == '__main__':
    app = CTP_App()
    app.mainloop()
