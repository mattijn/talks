import geopandas as gpd
import pandas as pd
import altair as alt
from shapely.geometry import Point
import warnings

warnings.simplefilter(action="ignore", category=FutureWarning)


def utils_extent(minx, miny, maxx, maxy):
    # define a listed polygon bounding box using  the left-hand-rule
    extent = [
        {
            "type": "Polygon",
            "coordinates": (
                ((maxx, maxy), (maxx, miny), (minx, miny), (minx, maxy), (maxx, maxy)),
            ),
        }
    ]
    return extent


def utils_condition(predicate, if_false):
    # define a two-foldcondition
    condition = {
        "condition": [
            {"param": predicate[0][0].name, "value": predicate[0][1], "empty": False},
            {"param": predicate[1][0].name, "value": predicate[1][1], "empty": False},
        ],
        "value": if_false,
    }
    return condition


def utils_chart_rose(utils_df_storms, param_hover, param_click, param_location):
    # define a rose chart
    # fix for https://github.com/vega/vega-lite/issues/7856
    w = alt.param(name="width", value=300)
    h = alt.param(name="height", value=300)

    c_rose_gridlines = (
        alt.Chart(utils_df_circles)
        .mark_arc(filled=False, stroke="gray", strokeWidth=0.3, radiusOffset=15, innerRadius=7.5)
        .encode(radius=alt.Radius("value:Q").stack(None))
    )

    c_rose_gridlabels = (
        alt.Chart(utils_df_circles)
        .mark_text(theta=alt.expr(3 * alt.expr.PI / 4), radiusOffset=15, innerRadius=7.5, align='left')
        .encode(radius=alt.Radius("value:Q").stack(None), text="label:N")
    )

    c_rose = (
        alt.Chart(utils_df_winddirs)
        .mark_arc(filled=False, stroke="lightslategray", strokeWidth=1, radiusOffset=15, innerRadius=7.5)
        .encode(theta="winddirection:N", radius=alt.datum(10000))
    )

    c_rose_label = (
        alt.Chart(utils_df_winddirs)
        .mark_text(radiusOffset=15, innerRadius=7.5)
        .transform_calculate(theta=alt.datum.winddirection * alt.expr.PI / 180)
        .encode(
            text="label:N", theta=alt.Theta("theta:Q").scale(None), radius=alt.datum(11000)
        )
    )

    c_windrose = (
        alt.Chart(utils_df_storms)
        .mark_arc(padAngle=0.01, cornerRadius=4, radiusOffset=15, innerRadius=7.5)
        .encode(
            theta=alt.Theta("wind_dir", type="nominal").sort(field="sector"),
            radius=alt.Radius(field="count", type="quantitative"),
            fill=alt.Fill(field="mean_windspeed", type="quantitative")
            .legend(offset=40, title="wind speed (m/s)")
            .scale(domain=[21, 26]),
            strokeWidth=utils_condition(
                [(param_hover, 2), (param_click, 3)], if_false=0
            ),
            stroke=utils_condition(
                [(param_hover, "red"), (param_click, "cyan")], if_false=None
            ),
            tooltip=[
                alt.Tooltip("mean_windspeed"),
                alt.Tooltip("count"),
                alt.Tooltip("wind_dir"),
                alt.Tooltip("location"),
            ],
        )
        .transform_filter(param_location)
        .add_params(param_hover, param_click, param_location, w, h)
    )

    chart_rose_all = (
        c_windrose + c_rose + c_rose_label + c_rose_gridlines + c_rose_gridlabels
    ).resolve_scale(theta="independent")
    return chart_rose_all


def utils_chart_single_hist(df, bin_start, bin_end, count, title, xtitle, domain):
    highlight_bar = alt.selection_point(on="mouseover", clear="mouseout")
    c = (
        alt.Chart(df, height=150, width=150, title=title)
        .mark_bar(tooltip=True, binSpacing=0.05, stroke="red")
        .encode(
            x=alt.X(field=bin_start, type="quantitative")
            .bin(binned=True, step=1)
            .title(None)
            .scale(domain=domain),
            x2=alt.X2(field=bin_end),
            y=alt.Y(field=count, type="quantitative").title(None),
            fill=alt.Fill(field=count, type="quantitative")
            .scale(type="log")
            .legend(None),
            strokeWidth=alt.condition(
                highlight_bar, alt.value(2), alt.value(0), empty=False
            ),
        )
        .add_params(highlight_bar)
    )
    return c


def utils_chart_hists(df_storms, param_wind_dir, param_location):
    pars = ["fase", "windfase", "windduur", "opzetduur"]
    domains = {
        "fase": [-6, 6],
        "windfase": [-24, 24],
        "windduur": [0, 60],
        "opzetduur": [0, 40],
    }
    titles = {
        "fase": "surge peak w.r.t. high tide (h)",
        "windfase": "wind peak w.r.t. high tide (h)",
        "windduur": "wind duration (h)",
        "opzetduur": "surge duration (h)",
    }
    c_pars = []
    for par in pars:
        domain = domains[par]
        title = titles[par]
        c_par = utils_chart_single_hist(
            df=df_storms,
            bin_start=par,
            bin_end=f"{par}_end",
            count=f"{par}_count",
            title=title,
            xtitle=par,
            domain=domain,
        )
        c_pars.append(c_par)
    return (
        alt.concat(*c_pars)
        .transform_filter(param_wind_dir)
        .transform_filter(param_location)
        .add_params(param_wind_dir, param_location)
    )


# define point data
d = {
    "location": ["delfzijl", "harlingen", "hoekvanholland", "vlissingen"],
    "geometry": [
        Point(6.93, 53.34),
        Point(5.40, 53.18),
        Point(4.06, 52.00),
        Point(3.55, 51.44),
    ],
}
utils_gdf_points = gpd.GeoDataFrame(d, crs="EPSG:4326")


# define windrose data
utils_df_winddirs = pd.DataFrame.from_dict(
    {"winddirection": [0, 90, 180, 270], "label": ["NORTH", "E", "SOUTH", "W"]}
)
utils_df_circles = pd.DataFrame.from_dict(
    {"value": [1000, 2500, 5000, 7500, 10000], "label": ["1K", "2.5", "5K", "7.5K", "no. storms"]}
)

# read rose data
utils_df_storms_rose_binned = pd.read_csv("4locs_storms_rose_binned.csv", index_col=0)


# read histogram data
utils_df_storms_hist_binned = pd.read_csv("4locs_storms_hists_binned.csv", index_col=0)
