google.charts.load('current', {'packages':['corechart']});

// Set a callback to run when the Google Visualization API is loaded.
google.charts.setOnLoadCallback(distrChart);


function distrChart() {

    var gstats = null;

    $.ajax({
    type: 'GET',
    async: false,
    url: 'globalStats',
    dataType: 'json',
    success: function (data) {
        gstats = data;
    }})

    var c = gstats["colors"]

    var cats = gstats["categories"]
    cats.unshift("Choices")
    var all = ["All Users"]
    var you = []

    for(var cat in gstats["categories"]){
        for(var key in gstats["distr_cat"]){
            if(key === gstats["categories"][cat]){
                all.push(gstats["distr_cat"][key])
            }
        }
    }

    var ytmp = {"1": 0, "2": 0, "3": 0, "4": 0, "5": 0, "6": 0, "7": 0, "8": 0, "9": 0, "10": 0, "-1": 0, "-2": 0, "0": 0}
    $.each(document.getElementsByClassName("choice"), function() {
        var val = this.getAttribute("value_id")
        if(val === null || val === undefined){
            return
        }
        ytmp[val] += 1;
    })


    var cc = 0
    for(var key in ytmp){
        if(cc < 13){
            you.push(ytmp[key])
        }
        cc += 1
    }
    you.push(you.shift())
    you.unshift("You")

    console.log(you)

    var data = google.visualization.arrayToDataTable([
    cats,
    all,
    you
    ]);

    var view = new google.visualization.DataView(data);


    var options = {
    title: "Distribution of answers by choices",
    isStacked: 'percent',
    height: 300,
    width: 600,
    legend: {position: 'none'},
    hAxis: {
        minValue: 0,
        ticks: [0, .25, .5, .75, 1]
    },
    series: {
        0: {color: c[0]},
        1: {color: c[1]},
        2: {color: c[2]},
        3: {color: c[3]},
        4: {color: c[4]},
        5: {color: c[5]},
        6: {color: c[6]},
        7: {color: c[7]},
        8: {color: c[8]},
        9: {color: c[9]},
        10: {color: c[10]},
        11: {color: c[11]},
        12: {color: c[12]}
    }
    };
    var chart = new google.visualization.BarChart(document.getElementById("distr_cat"));
    chart.draw(view, options);
}