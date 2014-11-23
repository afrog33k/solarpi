# -*- coding: utf-8 -*-
import calendar
from datetime import datetime, timedelta

from flask import Blueprint, render_template, flash
from sqlalchemy import extract, func, desc
from solarpi.public import helper
from solarpi.pvdata.helper import get_sec, get_todays_date

from solarpi.pvdata.models import PVData

blueprint = Blueprint("charts", __name__, url_prefix='/charts',
                      static_folder="../static")


@blueprint.route("/daily")
@blueprint.route("/daily/<date>")
def daily(date=get_todays_date().strftime('%Y-%m-%d')):
    error = None
    try:
        current_date = datetime.strptime(date, "%Y-%m-%d")
    except ValueError, TypeError:
        error = "invalid date, displaying today's data instead"
        current_date = get_todays_date()
    yesterday = current_date - timedelta(days=1)
    tomorrow = current_date + timedelta(days=1)

    # get photovoltaic data for the day
    pv = PVData.query.with_entities(PVData.created_at, PVData.current_power, PVData.daily_energy, PVData.dc_1_u,
                                    PVData.dc_2_u, PVData.ac_1_u, PVData.ac_2_u, PVData.ac_3_u).filter(
        PVData.created_at > current_date.strftime('%Y-%m-%d')).filter(
        PVData.created_at < tomorrow.strftime('%Y-%m-%d')).filter(PVData.current_power > 0).all()

    timestamps_pv = [
        1000 * calendar.timegm(
            datetime.strptime(d.created_at.split(".")[0], "%Y-%m-%dT%H:%M:%S")
            .replace(second=0).timetuple()) for d in pv]
    power_series_pv = [(int(d.current_power or 0)) for d in pv]
    daily_chart_data = [list(x) for x in zip(timestamps_pv, power_series_pv)]

    # voltages
    input_voltage_1_series_pv = [(int(d.dc_1_u or 0)) for d in pv]
    input_voltage_1_chart_data = [list(x) for x in zip(timestamps_pv, input_voltage_1_series_pv)]
    input_voltage_2_series_pv = [(int(d.dc_2_u or 0)) for d in pv]
    input_voltage_2_chart_data = [list(x) for x in zip(timestamps_pv, input_voltage_2_series_pv)]

    output_voltage_1_series_pv = [(int(d.ac_1_u or 0)) for d in pv]
    output_voltage_1_chart_data = [list(x) for x in zip(timestamps_pv, output_voltage_1_series_pv)]
    output_voltage_2_series_pv = [(int(d.ac_2_u or 0)) for d in pv]
    output_voltage_2_chart_data = [list(x) for x in zip(timestamps_pv, output_voltage_2_series_pv)]
    output_voltage_3_series_pv = [(int(d.ac_3_u or 0)) for d in pv]
    output_voltage_3_chart_data = [list(x) for x in zip(timestamps_pv, output_voltage_3_series_pv)]


    # get maxium photovoltaic data for ± 3 days
    pv_max = PVData.query.with_entities(func.strftime('%H:%M:00', PVData.created_at).label('pvdata_created_at'),
                                        func.max(PVData.current_power).label('pv_max')).filter(
        PVData.created_at >= (current_date - timedelta(days=3)).strftime('%Y-%m-%d')).filter(
        PVData.created_at <= (current_date + timedelta(days=3)).strftime('%Y-%m-%d')).filter(
        PVData.current_power > 0).group_by(
        func.strftime('%H:%M:00', PVData.created_at)).all()

    current_date_midnight = calendar.timegm(current_date.timetuple())
    timestamps_pv_max = [1000 * (get_sec(d.pvdata_created_at) + current_date_midnight)
                         for d in pv_max]
    series_pv_max = [(int(d.pv_max or 0)) for d in pv_max]
    daily_chart_max_data = [list(x) for x in zip(timestamps_pv_max, series_pv_max)]

    # additional data
    if len(pv) > 0:
        daily_energy = pv[-1].daily_energy
    else:
        daily_energy = 0

    return render_template("data/daily.html", data=daily_chart_data, data2=daily_chart_max_data,
                           yesterday=yesterday, today=current_date,
                           tomorrow=tomorrow, daily_energy=daily_energy, all_data=pv,
                           input_voltage_1_chart_data=input_voltage_1_chart_data,
                           input_voltage_2_chart_data=input_voltage_2_chart_data,
                           output_voltage_1_chart_data=output_voltage_1_chart_data,
                           output_voltage_2_chart_data=output_voltage_2_chart_data,
                           output_voltage_3_chart_data=output_voltage_3_chart_data,
                           error=error)


@blueprint.route("/monthly")
@blueprint.route("/monthly/<param>")
def monthly(param=datetime.now().strftime('%Y-%m')):
    try:
        month = datetime.strptime(param, "%Y-%m")
    except ValueError, TypeError:
        month = datetime.strptime('2014-07-01', "%Y-%m")

    data = PVData.query.with_entities(
        func.strftime('%Y-%m-%d', PVData.created_at).label('created_at'),
        func.max(PVData.daily_energy).label('daily_energy')).filter(
        PVData.created_at > datetime.now() - timedelta(days=30)).group_by(func.strftime('%Y-%m-%d', PVData.created_at))

    timestamps = [
        1000 * calendar.timegm(datetime.strptime(d.created_at, "%Y-%m-%d").timetuple())
        for d in data]
    series = [(float(d.daily_energy or 0)) for d in data]
    monthly_energy = sum(series)
    monthly_chart_data = [list(x) for x in zip(timestamps, series)]

    return render_template("data/monthly.html", data=monthly_chart_data, monthly_energy=monthly_energy)


@blueprint.route("/weekly")
def weekly():
    data = PVData.query.with_entities(
        func.strftime('%Y-%m-%d', PVData.created_at).label('created_at'),
        func.max(PVData.daily_energy).label('daily_energy')).filter(
        PVData.created_at > datetime.now() - timedelta(days=7)).group_by(func.strftime('%Y-%m-%d', PVData.created_at))

    timestamps = [
        1000 * calendar.timegm(datetime.strptime(d.created_at, "%Y-%m-%d").timetuple())
        for d in data]
    series = [(float(d.daily_energy or 0)) for d in data]
    seven_days_energy = sum(series)
    weekly_chart_data = [list(x) for x in zip(timestamps, series)]

    return render_template("data/weekly.html", data=weekly_chart_data, seven_days_energy=seven_days_energy)


@blueprint.route("/yearly")
def yearly():
    data = PVData.query.with_entities(
        func.max(PVData.total_energy.label('total_energy'))).group_by(
        func.strftime("%Y", PVData.created_at)).all()

    data = [int(x[0]) for x in data]
    total_energy = sum(data[1:])
    diffs = [y - x for x, y in zip(data, data[1:])]
    data = data[:1] + diffs
    years = [x for x in range(2013, 2013 + len(data))]
    yearly_data = [5741.82 for i in range(len(data))]

    return render_template("data/yearly.html", data=data, years=years, yearlyData=yearly_data,
                           total_energy=total_energy)