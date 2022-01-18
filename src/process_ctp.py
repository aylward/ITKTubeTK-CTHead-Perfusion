debug = True

import os
import sys
import subprocess
import pathlib

import tkinter as tk
import tkinter.filedialog
import tkinter.messagebox
from tkinter.ttk import Progressbar

import webbrowser

import itk
from itk import TubeTK as tube

import site
site.addsitedir('../lib')

from SCV_Lib import *

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

        self.cta_file = ""
        self.dsa_file = ""

        self.cbf_file = "../data/CTP-PerfusionMaps/CBF.nii"
        self.cbv_file = "../data/CTP-PerfusionMaps/CBV.nii"
        self.tmax_file = "../data/CTP-PerfusionMaps/Tmax.nii"
        self.ttp_file = "../data/CTP-PerfusionMaps/TTP.nii"

        self.dcm_in_dir = "./"
        self.dcm_out_dir = "./"

        self.process_out_dir = "./results"

        self.progress_status = ""

        self.title("SCV App")

        frm_title = tk.Frame(master=self)
        lbl_title = tk.Label(master=frm_title,
            text="Stroke Collateral Vessels",
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
    
        frm_scv = tk.Frame(master=self,
            relief=tk.RIDGE,
            borderwidth=5,
            bg="light sky blue",
            pady=5)
        lbl_scv = tk.Label(master=frm_scv,
            text="Process Perfusion files",
            bg="light sky blue").pack()

        frm_ctp = tk.Frame(master=frm_scv,
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
        btn_dsa= tk.Button(master=frm_ctp,
            text="Set 3D DSA file",
            command=self.hdl_dsa,
            width=20).pack()
        self.brain_segmented = tk.IntVar()
        ckb_brain_segmented = tk.Checkbutton(master=frm_ctp,
            text="Brain already segmented",
            variable=self.brain_segmented,
            bg="light sky blue").pack()
        frm_ctp.pack(padx=5,fill=tk.X)
    
        frm_perf = tk.Frame(master=frm_scv,
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
    
        frm_process = tk.Frame(master=frm_scv,
            relief=tk.GROOVE,
            borderwidth=5,
            bg="light sky blue",
            padx=5,
            pady=5)
        lbl_process = tk.Label(master=frm_process,
            text="Step 3: Process:",
            bg="light sky blue"
            ).pack(side=tk.LEFT)
        btn_process_out_dir = tk.Button(master=frm_process,
            text="Set output directory",
            command=self.hdl_process_out_dir,
            width=20
            ).pack(pady=5)
        btn_process = tk.Button(master=frm_process,
            text="Go!",
            command=self.hdl_process,
            bg="pale green",
            width=20
            ).pack(pady=5)
        self.lbl_progress = tk.Label(frm_process,
            text="Status: Idle",
            bg="light sky blue",
            width=40)
        self.lbl_progress.pack()
        self.pgb_progress = Progressbar(frm_process,
            orient=tk.HORIZONTAL,
            length=150,
            mode='determinate')
        self.pgb_progress.pack()
        self.pgb_subprogress = Progressbar(frm_process,
            orient=tk.HORIZONTAL,
            length=150,
            mode='determinate')
        self.pgb_subprogress.pack()
        frm_process.pack(padx=5,fill=tk.BOTH)
    
        frm_scv.pack(fill=tk.BOTH)


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

    def hdl_dcm(self):
        win_dcm = tk.Tk()

        frm_title = tk.Frame(master=win_dcm)
        lbl_title = tk.Label(master=frm_title,
            text="DICOM Conversion",
            pady=5).pack()
        frm_title.pack(fill=tk.BOTH)

        btn_dcm_in_dir = tk.Button(master=win_dcm,
            text="1) Set input directory",
            command=self.hdl_dcm_in_dir,
            width=20).pack()
        btn_dcm_out_dir = tk.Button(master=win_dcm,
            text="2) Set output directory",
            command=self.hdl_dcm_out_dir,
            width=20).pack()
        btn_dcm_process = tk.Button(master=win_dcm,
            text="3) Process",
            command=self.hdl_dcm_process,
            width=20).pack()

        win_dcm.mainloop()

    def hdl_dcm_in_dir(self):
        self.dcm_in_dir = os.path.realpath(tk.filedialog.askdirectory(
            initialdir=self.dcm_in_dir))

    def hdl_dcm_out_dir(self):
        self.dcm_out_dir = os.path.realpath(tk.filedialog.askdirectory(
            initialdir=self.dcm_out_dir))

    def hdl_dcm_process(self):
        dcm2niix = os.path.realpath( os.path.pathdir(__file__) +
            "/bin/dcm2niix.exe")
        subprocess.call([dcm2niix, "-o", self.dcm_out_dir, self.dcm_in_dir])

    def hdl_view(self):
        view_file = os.path.realpath(tk.filedialog.askopenfilename())
        uri = pathlib.Path(view_file).as_uri()
        path,name = os.path.split(view_file)
        url = "https://kitware.github.io/paraview-glance/app/"
        url += "?name=" + name
        url += "&url=" + uri
        print(url)
        webbrowser.open(url)
    
    def hdl_ctp(self):
        if len(self.ctp_files)>0:
            initialdir = os.path.dirname(self.ctp_files[0])
            self.ctp_files = list(tk.filedialog.askopenfilenames(
                initialdir=initialdir))
        else:
            self.ctp_files = list(tk.filedialog.askopenfilenames())
        self.cta_file = ""
        self.cbf_file = ""
        self.cbv_file = ""
        self.tmax_file = ""
        self.ttp_file = ""

    def hdl_cta(self):
        self.cta_file = os.path.realpath(tk.filedialog.askopenfilename(
            initialfile=self.cta_file))
        self.ctp_files = []
        self.cbf_file = ""
        self.cbv_file = ""
        self.tmax_file = ""
        self.ttp_file = ""

    def hdl_dsa(self):
        self.dsa_file = os.path.realpath(tk.filedialog.askopenfilename(
            initialfile=self.dsa_file))
        self.cbf_file = ""
        self.cbv_file = ""
        self.tmax_file = ""
        self.ttp_file = ""

    def hdl_cbf(self):
        self.cbf_file = os.path.realpath(tk.filedialog.askopenfilename(
            initialfile=self.cbf_file))

    def hdl_cbv(self):
        self.cbv_file = os.path.realpath(tk.filedialog.askopenfilename(
            initialfile=self.cbv_file))

    def hdl_tmax(self):
        self.tmax_file = os.path.realpath(tk.filedialog.askopenfilename(
            initialfile=self.tmax_file))

    def hdl_ttp(self):
        self.ttp_file = os.path.realpath(tk.filedialog.askopenfilename(
            initialfile=self.ttp_file))

    def hdl_process_out_dir(self):
        self.process_out_dir = os.path.realpath(tk.filedialog.askdirectory(
            initialdir=self.process_out_dir))

    def report_progress(self, label, percentage):
        self.progress_status = label
        self.lbl_progress['text'] = label
        self.pgb_progress['value'] = percentage
        self.pgb_subprogress['value'] = 0
        self.update()

    def report_subprogress(self, label, percentage):
        self.lbl_progress['text'] = self.progress_status+": "+label
        self.pgb_subprogress['value'] = percentage
        self.update()

    def hdl_process(self):
        if not os.path.exists(self.process_out_dir):
            os.mkdir(self.process_out_dir)

        cta_im = None
        dsa_im = None
        if len(self.ctp_files)>0:
            self.report_progress("Converting CTP to CTA",5)
            ctp_reg_output_dir = self.process_out_dir+"/CTP_Reg"
            if not os.path.exists(ctp_reg_output_dir):
                os.mkdir(ctp_reg_output_dir)
            ct_im,cta_im,dsa_im = scv_convert_ctp_to_cta(self.ctp_files,
                report_progress=self.report_subprogress,
                debug=True,
                output_dir=ctp_reg_output_dir)
            self.report_progress("Converting CTP to CTA",10)
            itk.imwrite(ct_im,self.process_out_dir+"/ct.mha",
                compression=True)
            itk.imwrite(cta_im,self.process_out_dir+"/cta.mha",
                compression=True)
            itk.imwrite(dsa_im,self.process_out_dir+"/dsa.mha",
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

        if self.brain_segmented.get() == 0:
            self.report_progress("Segmenting Brain",20)
            if cta_im != None:
                cta_brain_im = scv_segment_brain_from_cta(cta_im,
                    report_progress=self.report_subprogress,
                    debug=True)
                itk.imwrite(cta_brain_im,self.process_out_dir+"/cta_brain.mha",
                    compression=True)
            else:
                self.report_progress("ERROR",100)
                tk.messagebox.showerror(title="Error",
                    message="DSA must have prior brain segmentation \n" +
                            "or CTP or CTA must be included with it.")
                return

        in_im = cta_im
        in_brain_im = cta_brain_im
        in_name = "cta"
        if dsa_im != None:
            if self.brain_segmented.get() == 0:
                ImageMath = tube.ImageMath.New(Input=dsa_im)
                ImageMath.ReplaceValuesOutsideMaskRange(cta_brain_im,
                    0.001,9999,0)
                dsa_brain_im = ImageMath.GetOutput()
                itk.imwrite(dsa_brain_im,
                    self.process_out_dir+"/dsa_brain.mha",
                    compressed=True)
            in_im = dsa_im
            in_brain_im = dsa_brain_im
            in_name = "dsa"

        self.report_progress("Enhancing vessels",40)
        in_vess,in_brain_vess = scv_enhance_vessels_in_cta(
            in_im,
            in_brain_im,
            report_progress=self.report_subprogress,
            debug=True)
        itk.imwrite(dsa_vess,
            self.process_out_dir+"/"+in_name+"_vessels.mha",
            compression=True)
        itk.imwrite(dsa_brain_vess,
            self.process_out_dir+"/"+in_name+"_brain_vessels.mha",
            compression=True)

        self.report_progress("Extracting vessels",60)
        vess_mask,vess_so = scv_extract_vessels_from_cta(
            in_vess,
            in_brain_vess,
            report_progress=self.report_subprogress,
            debug=True,
            output_dir=ctp_reg_output_dir)
        
        self.report_progress("Generating report",90)
        self.report_progress("Done!",100)
    
if __name__ == '__main__':
    app = CTP_App()
    app.mainloop()
