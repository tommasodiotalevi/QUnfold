import sys
import os
import ROOT
import numpy as np
from QUnfold.root2numpy import TH1_to_numpy, TH2_to_numpy
from QUnfold.utils import normalize_response, lambda_optimizer
from utils.custom_logger import get_custom_logger
from unfolder import run_RooUnfold, run_QUnfold
from comparison import plot_comparison

log = get_custom_logger(__name__)

loaded_RooUnfold = ROOT.gSystem.Load("HEP_deps/RooUnfold/libRooUnfold.so")
if not loaded_RooUnfold == 0:
    log.error("RooUnfold not found!")
    sys.exit(0)


dirpath = "studies/data/"
rootfile = "unfolding_input.root"
reco_tree = "reco"
particle_tree = "particle"

var2label = {
    "pT_lep1": r"$P_T^{lep_1}$ [GeV]",
    "pT_lep2": r"$P_T^{lep_2}$ [GeV]",
    "m_l1l2": r"$M_{lep_1lep_2}$ [GeV]",
    "m_b1b2": r"$M_{b_1b_2}$ [GeV]",
    # "DR_b1b2": r"$\Delta R_{b_1b_2}$",
    # "eta_lep1": r"$\eta^{lep_1}$",
    # "eta_lep2": r"$\eta^{lep_2}$",
}

num_reads = 5000
num_toys = None
enable_hybrid = False
enable_quantum = False


if __name__ == "__main__":

    file = ROOT.TFile(f"{dirpath}{rootfile}", "READ")
    reco = file.Get(reco_tree)
    particle = file.Get(particle_tree)

    for var in var2label:
        log.info(f"Unfolding '{var}' variable...")

        th1_measured_mc = reco.Get(f"mc_{var}")
        th1_truth_mc = particle.Get(f"mc_particle_{var}")
        th2_response = reco.Get(f"particle_{var}_vs_{var}")
        th1_measured = reco.Get(var)
        th1_truth = particle.Get(f"particle_{var}")

        bins = th1_measured.GetNbinsX()
        xaxis = th1_measured.GetXaxis()
        bin_edges = [xaxis.GetBinLowEdge(bin) for bin in range(1, bins + 2)]
        binning = np.array([-np.inf] + bin_edges + [np.inf])

        ######################### RooUnfold #########################
        roounfold_response = ROOT.RooUnfoldResponse(
            th1_measured_mc, th1_truth_mc, th2_response
        )
        roounfold_response.UseOverflow(True)

        sol_MI, err_MI, cov_MI = run_RooUnfold(
            method="MI",
            response=roounfold_response,
            measured=th1_measured,
            num_toys=num_toys,
        )

        sol_IBU, err_IBU, cov_IBU = run_RooUnfold(
            method="IBU",
            response=roounfold_response,
            measured=th1_measured,
            num_toys=num_toys,
        )

        ########################## QUnfold ##########################
        truth = TH1_to_numpy(th1_truth, overflow=True)
        measured = TH1_to_numpy(th1_measured, overflow=True)
        response = normalize_response(
            response=TH2_to_numpy(th2_response, overflow=True),
            truth_mc=TH1_to_numpy(th1_truth_mc, overflow=True),
        )
        lam = lambda_optimizer(
            response=response, measured=measured, truth=truth, binning=binning
        )

        sol_SA, err_SA, cov_SA = run_QUnfold(
            method="SA",
            response=response,
            measured=measured,
            binning=binning,
            lam=lam,
            num_reads=num_reads,
            num_toys=num_toys,
        )

        if enable_hybrid:
            sol_HYB, err_HYB, cov_HYB = run_QUnfold(
                method="HYB",
                response=response,
                measured=measured,
                binning=binning,
                lam=lam,
                num_toys=num_toys,
            )

        if enable_quantum:
            sol_QA, err_QA, cov_QA = run_QUnfold(
                method="QA",
                response=response,
                measured=measured,
                binning=binning,
                lam=lam,
                num_reads=num_reads,
                num_toys=num_toys,
            )

        ######################### Comparison #########################
        solution = {"MI": sol_MI, "IBU": sol_IBU, "SA": sol_SA}
        error = {"MI": err_MI, "IBU": err_IBU, "SA": err_SA}
        covariance = {"MI": cov_MI, "IBU": cov_IBU, "SA": cov_SA}

        if enable_hybrid:
            solution.update({"HYB": sol_HYB})
            error.update({"HYB": err_HYB})
            covariance.update({"HYB": cov_HYB})
        if enable_quantum:
            solution.update({"QA": sol_QA})
            error.update({"QA": err_QA})
            covariance.update({"QA": cov_QA})

        fig = plot_comparison(
            solution,
            error,
            covariance,
            truth=truth,
            measured=measured,
            binning=binning,
            xlabel=var2label[var],
        )

        for ext in ["png", "pdf"]:
            dirpath = f"studies/img/paper_acat/{ext}"
            if not os.path.exists(dirpath):
                os.makedirs(dirpath)
            fig.tight_layout()
            fig.savefig(f"{dirpath}/{var}.{ext}")
