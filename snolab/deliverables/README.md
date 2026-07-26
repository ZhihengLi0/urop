# Deliverables — SNOLAB R4 Phonon Pulse Templates

Final products of the template project, organized by optimal-filter type.
All templates are 32768-bin `TH1D`, peak-normalized to 1; every figure carries
the full processing chain stamped on top.

```
1x1/   single-template (1x1) optimal-filter products
├── root_files/  Templates_SNOLAB_R4_zip{N}_2expfit_weighted.root  (13 zips)
│                one TH1D per channel (t2exp_zip{N}_{chan}): NRMSE-weighted
│                mean of all fit_ok fitted 2-exp curves, w = 1/max(NRMSE,0.01)^2
└── plots/       PT/ PS1/ PS2/ — per-zip figures of the summed 1x1 templates
                 (peak-normalized average of the per-channel nxm0 templates;
                 PT = all channels, PS1/PS2 = side 1/2), plus an all-zip
                 overview grid

nxm/   NxM multi-template optimal-filter products
├── root_files/  Templates_SNOLAB_R4_zip{N}_nxm_pca.root  (13 zips)
│                nxm{k}_zip{N}_{chan}: nxm0 = mean curve, nxm1..4 = PCA
│                components (population: fit_ok, NRMSE<=0.4, t_rise<=0.3ms;
│                common pretrigger 16050), all peak-normalized to 1
└── plots/       zip{N}_pca_templates.png — nxm0..4 per channel with
                 explained-variance ratios
```

Deployed copies in the official cdmsbats `PulseTemplates` layout
(top-level `zip{N}` directory with `{chan}`, `{chan}nxm0..4`, `PT`, `PS1`,
`PS2`) live on MSI:

```
/projects/standard/yanliusp/shared/software/cdmsbats_config/PulseTemplates/files/
    SNOLAB_R4_20260706_ZhihengLi_zip{N}.root        # 2-exp weighted family
    SNOLAB_R4_20260707_ZhihengLi_pca_zip{N}.root    # PCA nxm family
```

Generation scripts: `../lp_fit_align/scripts/`
(`write_2exp_templates_root.py`, `build_pca_templates.py`,
`normalize_pca_templates.py`, `plot_pt_ps_templates.py`,
`export_cdmsbats_templates.py`).

## Known substitution

Z7 PDS2 carries a low-frequency disturbance and cannot make a useful template
on its own; as a temporary solution its template entries (1x1 and nxm0..4, and
the PT/PS1/PS2 sums) are copies of the PDS1 template. The histogram titles
record the substitution. Applied by lp_fit_align/scripts/substitute_pds2_zip7.py.
