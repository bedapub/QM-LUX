# © 2026 Roche
# SPDX-License-Identifier: Apache-2.0
"""UV-Vis AUC (area-under-the-curve) descriptor computation.

Three complementary AUC representations are computed from the predicted UV-Vis
spectrum and merged into a single feature vector by :func:`run_AUCs_spectra`:

* ``from250`` — cumulative integrals starting at 250 nm
* ``to700``   — cumulative integrals ending at 700 nm
* ``100-1000`` — segment-by-segment integrals across the full range
"""

import numpy as np
import pandas as pd
from scipy.integrate import simpson, trapezoid


def AUC_meas_entire_from250_pred(df_c, seg, integral_method):
    """Compute cumulative AUC segments starting at 250 nm.

    For each compound, calculates the integral of the UV-Vis spectrum over
    windows ``[250, seg[0]]``, ``[250, seg[1]]``, … up to the second-to-last
    segment boundary.  Column names take the form ``"250-{boundary}pred"``.

    Parameters
    ----------
    df_c : pandas.DataFrame
        UV-Vis data with columns ``SRN``, ``lambda (nm)``,
        ``Epsilon (mL/cm/mol)``.  Modified in place — both value columns are
        converted from strings to numeric dtypes.
    seg : numpy.ndarray
        Segment boundary wavelengths (nm).  700 nm is appended internally as
        the final boundary.
    integral_method : {"trapz", "simps"}
        Numerical integration method: trapezoidal rule or Simpson's rule.

    Returns
    -------
    pandas.DataFrame
        One row per compound; columns ``SRN`` plus one AUC column per segment.

    Raises
    ------
    ValueError
        If any segment boundary exceeds the maximum wavelength in ``df_c``.
    UnboundLocalError
        If ``integral_method`` is neither ``"trapz"`` nor ``"simps"``.  No
        integrator is bound and the first integration attempt fails.
    """
    df_c["lambda (nm)"] = pd.to_numeric(df_c["lambda (nm)"], downcast="float")
    df_c["Epsilon (mL/cm/mol)"] = pd.to_numeric(
        df_c["Epsilon (mL/cm/mol)"], downcast="float"
    )

    if seg.max() > df_c["lambda (nm)"].max():
        raise ValueError(
            "At least one compound does not have absorption at the maximum "
            "wavelength provided in the AUC calculation range."
        )

    list_cmp = list(set(df_c["SRN"]))
    seg = np.append(seg, 700)
    print(seg)
    df_c = df_c.sort_values(by=["SRN", "lambda (nm)"], ascending=True)

    df_AUC = pd.DataFrame(columns=["SRN"])
    for i in range(len(seg)):
        df_AUC[[str(250) + "-" + str(seg[i]) + "pred"]] = ""
        if seg[i + 1] == seg[-1]:
            break

    if integral_method == "trapz":
        def AUC_integral(y, x):
            """Integrate ``y`` over ``x`` by the trapezoidal rule."""
            return trapezoid(y, x)
    elif integral_method == "simps":
        def AUC_integral(y, x):
            """Integrate ``y`` over ``x`` by Simpson's rule."""
            return simpson(y, x=x)

    columns = list(df_AUC)
    data_res = []
    for cpd in list_cmp:
        values = [cpd]
        cmp = df_c[df_c["SRN"] == cpd]
        for k in range(len(seg)):
            seg_cmp = cmp.loc[
                (cmp["lambda (nm)"] <= seg[k]) & (cmp["lambda (nm)"] >= 250)
            ]
            list_y = seg_cmp["Epsilon (mL/cm/mol)"].values.tolist()
            list_x = seg_cmp["lambda (nm)"].values.tolist()
            values.append(AUC_integral(list_y, list_x))
            zipped = zip(columns, values)
        cmp_dict = dict(zipped)
        cmp_dict["SRN"] = cpd
        data_res.append(cmp_dict)

    return pd.DataFrame.from_dict(data_res)


def AUC_meas_entire_to700_pred(df_c, seg, integral_method):
    """Compute cumulative AUC segments ending at 700 nm.

    For each compound, calculates the integral of the UV-Vis spectrum over
    windows ``[seg[0], 700]``, ``[seg[1], 700]``, ….  Column names take the
    form ``"{boundary}-700pred"``.

    Parameters
    ----------
    df_c : pandas.DataFrame
        UV-Vis data with columns ``SRN``, ``lambda (nm)``,
        ``Epsilon (mL/cm/mol)``.  Modified in place — both value columns are
        converted from strings to numeric dtypes.
    seg : numpy.ndarray
        Segment lower-boundary wavelengths (nm).  700 nm is appended internally.
    integral_method : {"trapz", "simps"}
        Numerical integration method.

    Returns
    -------
    pandas.DataFrame
        One row per compound; columns ``SRN`` plus one AUC column per segment.

    Raises
    ------
    ValueError
        If any segment boundary exceeds the maximum wavelength in ``df_c``.
    UnboundLocalError
        If ``integral_method`` is neither ``"trapz"`` nor ``"simps"``.  No
        integrator is bound and the first integration attempt fails.
    """
    df_c["lambda (nm)"] = pd.to_numeric(df_c["lambda (nm)"], downcast="float")
    df_c["Epsilon (mL/cm/mol)"] = pd.to_numeric(
        df_c["Epsilon (mL/cm/mol)"], downcast="float"
    )

    if seg.max() > df_c["lambda (nm)"].max():
        raise ValueError(
            "At least one compound does not have absorption at the maximum "
            "wavelength provided in the AUC calculation range."
        )

    list_cmp = list(set(df_c["SRN"]))
    seg = np.append(seg, 700)
    print(seg)
    df_c = df_c.sort_values(by=["SRN", "lambda (nm)"], ascending=True)

    df_AUC = pd.DataFrame(columns=["SRN"])
    for i in range(len(seg)):
        df_AUC[[str(seg[i]) + "-" + str(700) + "pred"]] = ""
        if seg[i + 1] == seg[-1]:
            break

    if integral_method == "trapz":
        def AUC_integral(y, x):
            """Integrate ``y`` over ``x`` by the trapezoidal rule."""
            return trapezoid(y, x)
    elif integral_method == "simps":
        def AUC_integral(y, x):
            """Integrate ``y`` over ``x`` by Simpson's rule."""
            return simpson(y, x=x)

    columns = list(df_AUC)
    data_res = []
    for cpd in list_cmp:
        values = [cpd]
        cmp = df_c[df_c["SRN"] == cpd]
        for k in range(len(seg)):
            seg_cmp = cmp.loc[
                (cmp["lambda (nm)"] <= 700) & (cmp["lambda (nm)"] >= seg[k])
            ]
            list_y = seg_cmp["Epsilon (mL/cm/mol)"].values.tolist()
            list_x = seg_cmp["lambda (nm)"].values.tolist()
            values.append(AUC_integral(list_y, list_x))
            zipped = zip(columns, values)
        cmp_dict = dict(zipped)
        cmp_dict["SRN"] = cpd
        data_res.append(cmp_dict)

    return pd.DataFrame.from_dict(data_res)


def AUC_meas_entire_pred(df_c, seg, integral_method):
    """Compute segment-by-segment AUC across the full wavelength range.

    For each compound, calculates the integral over consecutive windows
    ``[seg[0], seg[1]]``, ``[seg[1], seg[2]]``, ….  1000 nm is appended as
    the final boundary.  Column names take the form ``"{lo}-{hi}pred"``.

    Parameters
    ----------
    df_c : pandas.DataFrame
        UV-Vis data with columns ``SRN``, ``lambda (nm)``,
        ``Epsilon (mL/cm/mol)``.  Modified in place — both value columns are
        converted from strings to numeric dtypes.
    seg : numpy.ndarray
        Segment boundary wavelengths (nm).  1000 nm is appended internally.
    integral_method : {"trapz", "simps"}
        Numerical integration method.

    Returns
    -------
    pandas.DataFrame
        One row per compound; columns ``SRN`` plus one AUC column per segment.

    Raises
    ------
    ValueError
        If any segment boundary exceeds the maximum wavelength in ``df_c``.
    UnboundLocalError
        If ``integral_method`` is neither ``"trapz"`` nor ``"simps"``.  No
        integrator is bound and the first integration attempt fails.
    """
    df_c["lambda (nm)"] = pd.to_numeric(df_c["lambda (nm)"], downcast="float")
    df_c["Epsilon (mL/cm/mol)"] = pd.to_numeric(
        df_c["Epsilon (mL/cm/mol)"], downcast="float"
    )

    if seg.max() > df_c["lambda (nm)"].max():
        raise ValueError(
            "At least one compound does not have absorption at the maximum "
            "wavelength provided in the AUC calculation range."
        )

    list_cmp = list(set(df_c["SRN"]))
    seg = np.append(seg, 1000)
    print(seg)
    df_c = df_c.sort_values(by=["SRN", "lambda (nm)"], ascending=True)

    df_AUC = pd.DataFrame(columns=["SRN"])
    for i in range(len(seg) - 1):
        df_AUC[[str(seg[i]) + "-" + str(seg[i + 1]) + "pred"]] = ""
        if seg[i + 1] == seg[-1]:
            break

    if integral_method == "trapz":
        def AUC_integral(y, x):
            """Integrate ``y`` over ``x`` by the trapezoidal rule."""
            return trapezoid(y, x)
    elif integral_method == "simps":
        def AUC_integral(y, x):
            """Integrate ``y`` over ``x`` by Simpson's rule."""
            return simpson(y, x=x)

    columns = list(df_AUC)
    data_res = []
    for cpd in list_cmp:
        values = [cpd]
        cmp = df_c[df_c["SRN"] == cpd]
        for k in range(len(seg) - 1):
            seg_cmp = cmp.loc[
                (cmp["lambda (nm)"] <= seg[k + 1]) & (cmp["lambda (nm)"] >= seg[k])
            ]
            list_y = seg_cmp["Epsilon (mL/cm/mol)"].values.tolist()
            list_x = seg_cmp["lambda (nm)"].values.tolist()
            values.append(AUC_integral(list_y, list_x))
            zipped = zip(columns, values)
        cmp_dict = dict(zipped)
        cmp_dict["SRN"] = cpd
        data_res.append(cmp_dict)

    return pd.DataFrame.from_dict(data_res)


def run_AUCs_spectra(df):
    """Compute and merge all AUC descriptor sets from a UV-Vis DataFrame.

    Calls the three AUC functions with the wavelength segments used for model
    training and merges them on ``SRN``.

    Parameters
    ----------
    df : pandas.DataFrame
        UV-Vis data with columns ``SRN``, ``lambda (nm)``,
        ``Epsilon (mL/cm/mol)``.  Modified in place — the wavelength and
        epsilon columns are converted from strings to numeric dtypes.

    Returns
    -------
    pandas.DataFrame
        One row per compound and 114 columns: ``SRN``, every individual
        segment column from the three AUC functions, and the three packed
        list-valued descriptor columns ``100-1000`` (the 90 contiguous
        100–1000 nm segments), ``from250`` (11 cumulative windows opening at
        250 nm) and ``to700`` (11 cumulative windows closing at 700 nm).  The
        packed columns are what the models consume; the individual segment
        columns are retained alongside them, not dropped.
    """
    seg = np.arange(260, 360, 10)
    UV_pred_AUC_250 = AUC_meas_entire_from250_pred(df, seg, "trapz")

    seg = np.arange(250, 360, 10)
    UV_pred_AUC_700 = AUC_meas_entire_to700_pred(df, seg, "trapz")

    seg = np.arange(100, 1000, 10)
    UV_pred_AUC_all = AUC_meas_entire_pred(df, seg, "trapz")

    UV_pred_AUC = pd.merge(UV_pred_AUC_250, UV_pred_AUC_700, on="SRN")
    UV_pred_AUC = pd.merge(
        UV_pred_AUC_all,
        UV_pred_AUC.loc[:, UV_pred_AUC.columns != "250-260pred"],
        on="SRN",
    )

    col250 = [
        "250-260pred", "250-270pred", "250-280pred", "250-290pred",
        "250-300pred", "250-310pred", "250-320pred", "250-330pred",
        "250-340pred", "250-350pred", "250-700pred",
    ]
    col700 = [
        "250-700pred", "260-700pred", "270-700pred", "280-700pred",
        "290-700pred", "300-700pred", "310-700pred", "320-700pred",
        "330-700pred", "340-700pred", "350-700pred",
    ]

    col_remove = []
    for i, j in zip(col250, col700):
        col_remove.append(i)
        col_remove.append(j)

    col = UV_pred_AUC.loc[:, ~UV_pred_AUC.columns.isin(col_remove)].columns
    col = list(col[1:])
    col.append("250-260pred")
    col.sort()

    UV_pred_AUC = UV_pred_AUC.reset_index(drop=True)
    UV_pred_AUC["100-1000"] = UV_pred_AUC[col].values.tolist()
    UV_pred_AUC["from250"] = UV_pred_AUC[col250].values.tolist()
    UV_pred_AUC["to700"] = UV_pred_AUC[col700].values.tolist()

    return UV_pred_AUC
