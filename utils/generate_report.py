import cv2 
import datetime
import matplotlib.pyplot as plt
from matplotlib import gridspec
from adjustText import adjust_text

MD_axis_coordinate_dict = {
    5:[90,122],     # 5-4
    4:[122,146],    # 4-3
    3:[146,172],    # ...
    2:[172, 197],
    1:[197,224],
    0:[224,260],
    -0.5:[260,288],
    -1:[288,318],
    -1.5:[318,348],
    -2:[348,374],
    -2.5:[274,399],
    -3:[399,419],
    -3.5:[419,435],
    -4:[435,466],
    -5:[466,495],
    -6:[495,521],
    -7:[521,545],
    -8:[545,564],
    -9:[564,584],
    -10:[584,598],
    -11:[598,614],
    -12:[614,625],
    -13:[625,637],
    -14:[637,647],
    -15:[647, 694],
    -20:[694,730],
    -25:[730,757],
    -30:[747,757]
}

PSD_axis_coordinate_dict = {
    0:[108,204],     # 5-4
    2:[204,260],    # 4-3
    3:[260,306],    # ...
    4:[306,344],
    5:[344,378],
    6:[378,407],
    7:[407,435],
    8:[435,452],
    9:[452,469],
    10:[469,483],
    11:[483,498],
    12:[498,514],
    13:[514,528],
    14:[528,539],
    15:[539,561],
    17:[561,577],
    19:[577,577]
}


def generate_report(one_eye_dict, to_save_path, group_type_bool=False):

    img = cv2.imread("glaucoma-staging.png")
    fig = plt.figure(figsize=(18, 12), dpi=400)
    spec = gridspec.GridSpec(ncols=1, nrows=2,
                            height_ratios=[8, 1])

    ax0 = fig.add_subplot(spec[0])
    ax0.imshow(img, alpha=0.3)

    x,y,label = [], [], []
    dates = list(one_eye_dict.keys())
    dates.sort()
    for date in dates:
        MD, PSD = one_eye_dict[date]

        MD_keys = list(MD_axis_coordinate_dict.keys())
        PSD_keys = list(PSD_axis_coordinate_dict.keys())

        for i in range(len(MD_keys)-1):
            if MD_keys[i] >= MD and MD_keys[i+1] < MD:
                MD_coordinate = (MD-MD_keys[i])/(MD_keys[i+1] - MD_keys[i]) * (MD_axis_coordinate_dict[MD_keys[i]][1] - MD_axis_coordinate_dict[MD_keys[i]][0]) + MD_axis_coordinate_dict[MD_keys[i]][0]

        for i in range(len(PSD_keys)-1):
            if PSD_keys[i] <= PSD and PSD_keys[i+1] > PSD:
                PSD_coordinate = (PSD-PSD_keys[i])/(PSD_keys[i+1] - PSD_keys[i]) * (PSD_axis_coordinate_dict[PSD_keys[i]][1] - PSD_axis_coordinate_dict[PSD_keys[i]][0]) + PSD_axis_coordinate_dict[PSD_keys[i]][0]
        x.append(MD_coordinate)
        y.append(PSD_coordinate)
        ax0.scatter(MD_coordinate,PSD_coordinate,c='black', s=8)
        # plt.annotate(date.strftime('%Y-%m-%d'), (MD_coordinate,PSD_coordinate), c='black')
    # texts = [plt.text(x[i], y[i], dates[i].strftime('%Y-%m-%d'),fontsize=8) for i in range(len(x))] 
    if not group_type_bool:
        # put index onto plot
        texts = [plt.text(x[i], y[i], int(i), fontsize=16) for i in range(len(x))] 
        adjust_text(texts, arrowprops=dict(arrowstyle="-", color='red', lw=0.5))
        ax0.plot(x,y,c='black')

        ax1 = fig.add_subplot(spec[1])
        table_values = []
        idx = 0
        for per_date in one_eye_dict.keys():
            table_values.append([idx, per_date.strftime("%m/%d/%Y"), one_eye_dict[per_date][0], one_eye_dict[per_date][1]])
            idx += 1
        ax1.table(table_values, colLabels=['Index', 'DATE', 'MD', 'PSD'])
        ax1.get_xaxis().set_visible(False)
        ax1.get_yaxis().set_visible(False)
        ax1.axis('off')

    # hide the axis display
    ax0.get_xaxis().set_visible(False)
    ax0.get_yaxis().set_visible(False)

    plt.savefig(to_save_path)
    # plt.show()
    return 

if __name__ == "__main__":
    dict_test = {0: {datetime.datetime(2019, 10, 22, 0, 0): [-23.85, 7.9]}, 1: {datetime.datetime(2018, 9, 16, 0, 0): [-10.91, 4.99], datetime.datetime(2018, 10, 22, 0, 0): [-15.08, 5.39], datetime.datetime(2020, 10, 22, 0, 0): [-20.08, 7.39]}}
    generate_report(dict_test[1])