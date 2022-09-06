

startKinkId = 1001;

function checkForProgress(){
    res = false;
    for (var key in localStorage){
        if(!key.startsWith("meta")){
            res = true
            break
        }
    }
    return res
}

function checkForMeta() {
    res = false;
    for (var key in localStorage){
        if(key.startsWith("meta")){
            res = true
            break
        }
    }
    return res

}

function findLastEmpty() {




}

function start(){


}


function buildStart() {



}


function buildMeta() {
    $.ajax({
    type: 'GET',
    url: 'config',
    dataType: 'json',
    success: function (data) {
            var cat = data['categories']
            $.each(cat, function(index) {
                if(this['default'] == true){
                    cat.splice(index, 1)
                }
            })
            window.choices = cat
            const urlParams = new URLSearchParams(window.location.search);
            var err = urlParams.get('err')
            console.log(err)

            var meta = data['meta']
            document.getElementById('meta_name').placeholder = meta['name'][0]
            document.getElementById('meta_name').onchange = meta_changed
            if(err === '1'){
                if(window.localStorage.getItem('meta_name') !== '' && window.localStorage.getItem('meta_name') !== null){
                    window.location.replace('/meta')
                }
                document.getElementById('meta_name').classList.add('err')
            }

            for(let i = meta['age'][0]; i < meta['age'][1]+1; i++){
                var option = document.createElement('option')
                option.innerText = i
                 document.getElementById('meta_age').appendChild(option)
            }
            document.getElementById('meta_age').onchange = meta_changed
            $.each(meta['sex'], function() {
                var option = document.createElement('option')
                option.innerText = this
                document.getElementById('meta_sex').appendChild(option)
            })
            document.getElementById('meta_sex').onchange = meta_changed
            $.each(meta['fap_freq'], function() {
                var option = document.createElement('option')
                option.innerText = this
                document.getElementById('meta_fap_freq').appendChild(option)
            })
            document.getElementById('meta_fap_freq').onchange = meta_changed
            $.each(meta['sex_freq'], function() {
                var option = document.createElement('option')
                option.innerText = this
                document.getElementById('meta_sex_freq').appendChild(option)
            })
            document.getElementById('meta_sex_freq').onchange = meta_changed
            $.each(meta['body_count'], function() {
                var option = document.createElement('option')
                option.innerText = this
                document.getElementById('meta_body_count').appendChild(option)
            })
            document.getElementById('meta_body_count').onchange = meta_changed

            document.getElementById('meta_name').value = window.localStorage.getItem('meta_name')
            document.getElementById('meta_age').value = window.localStorage.getItem('meta_age')
            document.getElementById('meta_sex').value = window.localStorage.getItem('meta_sex')
            document.getElementById('meta_fap_freq').value = window.localStorage.getItem('meta_fap_freq')
            document.getElementById('meta_sex_freq').value = window.localStorage.getItem('meta_sex_freq')
            document.getElementById('meta_body_count').value = window.localStorage.getItem('meta_body_count')
    }})
}


function checkForProgress(){
    if(window.localStorage.getItem('meta_name') === '' || window.localStorage.getItem('meta_name') === null){
        return;
    }
    window.id_left_off = "1001";
    $.ajax({
    type: 'GET',
    url: 'byid',
    dataType: 'json',
    success: function (data) {
        $.each(Object.keys(data), function(){
            var cols = JSON.parse(window.localStorage.getItem(this));
            if(!cols.includes("0")){
                window.id_left_off = this
            } else {
                return false;
            }

        })

        console.log("Result: " + window.id_left_off)
        if(window.id_left_off !== "1001"){
            document.getElementById("tip_progress").classList.remove("hidden");
            document.getElementById("continue").onclick = function(){
            window.location.href = '/quiz?id=' + window.id_left_off;
        }
    }
    }})

}


function getProgress() {
    var total_fields = 0;
    var fields_filled = 0;
    $.each(Object.keys(window.localStorage), function(){
        if(!this.startsWith("meta")){
            var cols = JSON.parse(window.localStorage.getItem(this));
            total_fields += cols.length;
            for(var i = 0; i < cols.length; i++){
                if(cols[i] !== "0"){
                    fields_filled += 1;
                }
            }
        }
    })

    window.total_fields = total_fields;
    window.fields_filled = fields_filled;
    updateProgress();
}

function updateProgress() {
    var progress = Math.round(window.fields_filled / window.total_fields * 1000)/10;
    document.getElementById("msprog").innerText = progress + "%";
}



function fillChoices() {
    var id = parseInt(document.getElementById("kinkID").innerText);
    var vals = JSON.parse(window.localStorage.getItem(id))
    var cols = document.getElementsByClassName('mchoices');
    for(var i = 0; i < vals.length; i++){
        if(vals[i] === "0"){
            continue;
        }

        for(var j = 0; j < cols[i].children.length; j++){
            if(cols[i].children[j].value === vals[i] && cols[i].children[j].nodeName === "BUTTON"){
                cols[i].children[j].click()
            }

        }

    }

}


function submit(){
    var lc = window.localStorage
    var kinks = []
    var meta = []

    if(lc.getItem('meta_name') === null ||lc.getItem('meta_name') === ''){
        window.location.href = '/meta?err=1'
    } else if(lc.getItem('meta_name').length > 100) {
         window.location.href = '/meta?err=1'
    }else {
        $.each(Object.keys(lc), function(){
            val = lc.getItem(this);
            if(this.startsWith('meta_')){
                meta.push({"id": this.valueOf(), "val": val})
            } else {
                kinks.push({"id": parseInt(String(this).slice(0, 5)), "val": val})
            }
        })

        fetch('/', {
            method: 'POST',
            headers: {'Content-Type': 'application/json'},
            body: JSON.stringify({"meta": meta, "kinks": kinks}),
        }).then(res => {
            window.location.href = '/results?token=' + $.cookie('token') + "&justCreated=true"
        })
    }
}


function enterChoice(sender){
    var parent = sender.parentNode;
    var val = sender.value;
    var id = parseInt(document.getElementById("kinkID").innerText);
    window.fields_filled += 1;
    updateProgress();
    $.each(parent.childNodes, function(){
        if(this.nodeName === "#text"){
            return;
        }

        if(this.classList.contains("choice")){
            this.classList.add("hidden");
        }
        if(this.classList.contains("entered") && this.getAttribute("value") === val){
            var pos = this.getAttribute("index")
            updateLS(id, val, parseInt(pos))

            this.classList.remove("hidden");
            var tdiv = this.children[0]
            if (tinycolor(this.style.backgroundColor).getBrightness() < 128) {
                tdiv.style.setProperty('color', 'white', 'important')
            } else {
                tdiv.style.setProperty('color', 'black', 'important')
            }
        }
    })
}

function removeChoice(sender){
    var parent = sender.parentNode;
    var val = sender.value;
    var id = parseInt(document.getElementById("kinkID").innerText);
    window.fields_filled -= 1;
    updateProgress();
    $.each(parent.childNodes, function(){
        if(this.nodeName === "#text"){
            return;
        }

        if(this.classList.contains("choice")){
            this.classList.remove("hidden");
        }
    })
    sender.classList.add("hidden")
    var pos = sender.getAttribute("index")
    updateLS(id, "0", parseInt(pos))
}


function updateLS(id, value, pos){
    var tmp = JSON.parse(window.localStorage.getItem(id))
    tmp[pos] = value
    var val = JSON.stringify(tmp)
    if (val == null){
                    window.alert(id + tmp.toString())
                }
    window.localStorage.setItem(id, val)

}