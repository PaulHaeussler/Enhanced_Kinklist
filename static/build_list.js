function sleep(ms) {
    return new Promise(resolve => setTimeout(resolve, ms));
}

function enterChoice(sender){
    var div = sender.srcElement.parentNode;
    var id = sender.srcElement.value;
    var tr = div;
    var td = null;
    var pos = 0;
    while(true) {
        if (tr.nodeName === "TR"){
            break;
        }
        if (tr.nodeName === "TD"){
            td = tr;
        }
        tr = tr.parentNode;
    }
    for(var i = 0; i < tr.childNodes.length; i++) {
        if (tr.childNodes[i] === td) {
            pos = i
        }
    }

    var kc = tr.childNodes[0]



    var kink = kc.childNodes[0].childNodes[0].childNodes[0].textContent;
    updateCookie(kink, id, pos)
    div.innerHTML = ''
    var btn = document.createElement('btn');
    btn.classList.add('entered')
    var lu = lookupChoice(id)
    var tdiv = document.createElement('div');
    tdiv.classList.add('choiceText')
    tdiv.innerText = lu[0]
    div.style.backgroundColor = lu[1]
    var index = sender.srcElement.getAttribute("index")

    window.doneKinks += 1;
    window.remnKinks -= 1;

    updateProgress()
    btn.setAttribute("index", index)
    btn.value = id
    btn.onclick = removeChoice
    if (tinycolor(lu[1]).getBrightness() < 128) {
        btn.style.color = 'white'
        tdiv.style.color = 'white'
    } else {
        btn.style.color = 'black'
        tdiv.style.color = 'black'
    }
    btn.appendChild(tdiv)
    div.appendChild(btn)
}

function removeChoice(sender){
    var div = sender.srcElement;
    var id = sender.srcElement.value;
    var tr = div;
    var td = null;
    var cdiv = null;
    var pos = 0;
    while(true) {
        if (tr.nodeName === "TR"){
            break;
        }
        if (tr.nodeName === "TD"){
            td = tr;
        }
        if (tr.className === "cdiv") {
            cdiv = tr;
        }
        tr = tr.parentNode;
    }
    for(var i = 0; i < tr.childNodes.length; i++) {
        if (tr.childNodes[i] === td) {
            pos = i
        }
    }

    var kc = tr.childNodes[0]
    var kink = kc.childNodes[0].childNodes[0].childNodes[0].textContent;
    var index = sender.srcElement.getAttribute("index");

    window.doneKinks -= 1;
    window.remnKinks += 1;

    updateProgress()
    updateCookie(kink, id, pos)
    cdiv.innerHTML = ''
    cdiv.style.backgroundColor = ''
    buildOptions(cdiv, kink, pos, index)
}


function updateProgress(){
    var progress = Math.round(window.doneKinks / (window.doneKinks + window.remnKinks) * 1000)/10;

    var s = document.getElementById("prog_tip")
    s.innerText = progress + "%"

    var bar = document.getElementById("prog_bar")
    bar.style.height = window.innerHeight * 0.65 * progress/100 + "px";

    var tip = document.getElementById("prog_tip")
    tip.style.marginTop = window.innerHeight * 0.65 * progress/100 - 11 + 42 + "px"
}


function buildOptions(parent, kink, pos, index){

    $.each(window.choices, function(){
        var btn = document.createElement('button');
        btn.value = this['id']
        btn.classList.add('choice')
        btn.setAttribute("index", index)
        btn.style.backgroundColor = this['color']
        btn.onclick = enterChoice
        if(this["id"] == "5" || this["id"] == "10") {
            btn.style.marginRight = "15px"
        }
        var k = lookup_group(kink)
        if(k["only_havent_tried"]){
            console.log()
        }

        if(!(this["have_tried"] === true && k["only_havent_tried"] === true)) {
            parent.appendChild(btn)
        }

    })

}

function lookupChoice(id){
    var res = ['ERROR', 'red']
    $.each(window.choices, function(){
        if((this['id'] + '') == id){
            res = [this['description'], this['color']]
        }
    })
    return res
}

function lookup_id(kink){
    var res = null
    $.each(window.groups, function() {
        $.each(this['rows'], function() {
            if(this['description'] == kink){
                res = this['id']
            }
        })
    })
    return res
}


function lookup(kink){
    var res = null
    $.each(window.groups, function() {
        $.each(this['rows'], function() {
            if(this['description'] == kink){
                res = this
            }
        })
    })
    return res
}


function lookup_group(kink){
    var res = null
    $.each(window.groups, function() {
        var g = this;
        $.each(this['rows'], function() {
            if(this['description'] == kink){
                res = g
            }
        })
    })
    return res
}



function encodeCookie(values) {
    var result = ""
    Object.keys(values).forEach(function(key){
        result += key + "="
        $.each(values[key], function(){
            result += values[key] + "="
        })
        result += "#"
    })
    return result
}

function updateCookie(kink, value, pos){
    var id = lookup_id(kink)
    var tmp = JSON.parse(window.localStorage.getItem(id))
    tmp[pos-1] = value
    var val = JSON.stringify(tmp)
    if (val == null){
                    window.alert(id + tmp.toString())
                }
    window.localStorage.setItem(id, val)

}





function getCookieVal(kink, pos){
    var id = lookup_id(kink)
    var tmp = JSON.parse(window.localStorage.getItem(id))
    return tmp[pos-1]
}


function setupLocalStorage(){
    $.each(decodeURIComponent($.cookie('values')).split('#'), function(){
        if(this.length > 2) {
            var tmp = this.split('=')
            var list = []
            for(let i = 1; i < tmp.length; i++){
                if(tmp[i] != ""){
                    list.push(tmp[i])
                }
            }
            window.localStorage.setItem(tmp[0], JSON.stringify(list))
        }
    })
}

function checkLocalStorage(){
    $.each($.cookie('values').split('#'), function(){
        if(this !== ''){
            var splt = this.split('=')
            var val = window.localStorage.getItem(splt[0])
            if(val === null){
                list = []
                for(var i = 1; i < splt.length; i++){
                    list.push(splt[i])
                }
                var val = JSON.stringify(list)
                window.localStorage.setItem(splt[0], val)
            }
        }



    })


}

function meta_changed(sender){
    var src = sender.srcElement
    src.classList.remove('err')
    window.localStorage.setItem(src.id, src.value)
}

function test(){
        var t = '5009=0=0'
        if(t.length > 2) {
            var tmp = t.split('=')
            var list = []
            for(let i = 1; i < tmp.length; i++){
                if(tmp[i] != ""){
                    list.push(tmp[i])
                }
            }
            console.log(tmp[0])
            console.log(JSON.stringify(list))
        }
}


function build_list(){

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
            var root = document.getElementById('choices_container')
            $.each(cat, function() {
                var cdiv = document.createElement('div');
                cdiv.classList.add('dchoice')
                var rspan = document.createElement('span')
                var tspan = document.createElement('span')
                rspan.classList.add('choice')
                rspan.classList.add('noedit')
                rspan.style.backgroundColor = this['color']
                tspan.className = 'choice-text'
                tspan.textContent = this['description']
                cdiv.appendChild(rspan)
                cdiv.appendChild(tspan)
                root.appendChild(cdiv)
            })

            var meta = data['meta']
            document.getElementById('meta_name').placeholder = meta['name'][0]
            document.getElementById('meta_name').onchange = meta_changed
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

            var submit = document.createElement('btn')
            submit.classList.add('submit')
            submit.innerText = 'Submit'
            submit.onclick = submit_results

            var coll = document.createElement('button')
            coll.id = 'missingKinkColl'
            coll.innerText = 'My Kink is missing :('
            coll.classList.add('collapsible')
            var content = document.createElement('div')
            content.classList.add('content')
            var sp = document.createElement('span')
            sp.innerText = "Please enter and describe the missing kink, ideally including a fitting category and image:"
            var ta = document.createElement('textarea')
            ta.classList.add('ta')
            ta.id = 'missingKink'
            ta.maxLength = 2000
            content.appendChild(sp)
            content.appendChild(ta)
            var send = document.createElement('btn')
            send.id = 'missingKinkSubmit'
            send.classList.add('submit')
            send.style.width = '100%'
            send.style.padding = '5px'
            send.innerText = 'Pls add!'

            send.onclick = function(){
                var content = document.getElementById('missingKink').value
                fetch('/missingKink', {
                    method: 'POST',
                    headers: {'Content-Type': 'application/json'},
                    body: JSON.stringify({"missingkink": content}),
                }).then(res => function(){
                })
                console.log("Sent")
                location.reload()
            }
            content.appendChild(send)


            var reset = document.createElement('btn')
            reset.classList.add('reset')
            reset.innerText = 'Reset All'
            reset.onclick = function(){
                if(confirm('Are you really sure? This will reset all data that you have entered!')){
                    window.localStorage.clear();
                    $.cookie("user", null, { path: '/' })
                    $.cookie("values", null, { path: '/' })
                    window.location.reload();
                    $('html, body').animate({ scrollTop: 0 }, 'fast');
                }
            }
            var resetUser = document.createElement('btn')
            resetUser.classList.add('reset')
            resetUser.innerText = 'Reset User'
            resetUser.onclick = function(){
                if(confirm('Are you really sure? This will reset the metadata (name, age, ...) that you entered. Your choices will not be affected.')){
                    $.cookie("user", null, { path: '/' })
                    window.localStorage.removeItem('meta_name');
                    window.localStorage.removeItem('meta_sex_freq');
                    window.localStorage.removeItem('meta_sex');
                    window.localStorage.removeItem('meta_age');
                    window.localStorage.removeItem('meta_fap_freq');
                    window.localStorage.removeItem('meta_body_count');
                    window.location.reload();
                    $('html, body').animate({ scrollTop: 0 }, 'fast');
                }
            }
            document.getElementById('footer_container').appendChild(submit)
            document.getElementById('footer_container').appendChild(coll)
            document.getElementById('footer_container').appendChild(content)
            document.getElementById('footer_container').appendChild(reset)
            document.getElementById('footer_container').appendChild(resetUser)

            buildCollapsibles()

            var kinkgroups = data['kink_groups']
            window.doneKinks = 0
            window.remnKinks = 0
            window.totalRows = 0

            $.each(kinkgroups, function() {
                window.remnKinks += this["rows"].length * this["columns"].length;
                window.totalRows += this["rows"].length;
            })



            var index = 0
            window.groups = kinkgroups
            root = document.getElementById('group_container')
            $.each(kinkgroups, function() {
                var group = this

                var container = document.createElement('div');
                container.classList.add('kinkgroup')
                container.classList.add('bgc')
                var title = document.createElement('h3');
                title.textContent = this['description']
                title.classList.add('groupTitle')
                var desc = document.createElement('span');
                desc.textContent = this['tip']
                desc.classList.add('groupDesc')
                var table = document.createElement('table')
                table.classList.add('kinks')
                var headerrow = document.createElement('tr')
                var cols = this['columns'].length
                var kink_header = document.createElement('th')
                kink_header.innerText = ""
                headerrow.appendChild(kink_header)

                $.each(this['columns'], function(){
                    var th = document.createElement('th')
                    th.textContent = this
                    th.classList.add('header')
                    headerrow.appendChild(th)
                })
                table.appendChild(headerrow)

                $.each(this['rows'], function(){
                    var row = document.createElement('tr')
                    var ktd = document.createElement('td')
                    ktd.classList.add('kinkCell')
                    var kdiv = document.createElement('div')
                    kdiv.classList.add('kdiv')
                    var kink_title = document.createElement('label')
                    kink_title.classList.add('kinkTitle')
                    kink_title.textContent = this['description']
                    var kink_desc = document.createElement('label')
                    kink_desc.classList.add('kinkDesc')
                    kink_desc.textContent = this['tip']

                    var imglink = 'static/imgs/' + this['id'] + '.jpg'
                    var hdiv = document.createElement('div')
                    hdiv.classList.add('hdiv')
                    var tipdiv = document.createElement('div')
                    tipdiv.classList.add('tipdiv')
                    var tdiv = document.createElement('div')
                    tdiv.classList.add('tooltip')
                    var a = document.createElement('a')
                    a.setAttribute('target', '_blank')
                    a.setAttribute('href', imglink)
                    var img = document.createElement('img')
                    img.setAttribute('src', "static/img.svg")
                    img.classList.add('icon')
                    a.appendChild(img)
                    tdiv.appendChild(a)
                    var timg = document.createElement('img')
                    timg.classList.add('tipimg')
                    timg.setAttribute('src', imglink)
                    timg.onerror = function (image) {
                        var p = image.srcElement.parentNode.parentNode;
                        p.innerHTML = "";
                        return true;
                    }
                    tipdiv.appendChild(timg)
                    tdiv.appendChild(tipdiv)
                    kdiv.appendChild(kink_title)
                    kdiv.appendChild(kink_desc)
                    hdiv.appendChild(kdiv)
                    hdiv.appendChild(tdiv)
                    ktd.appendChild(hdiv)
                    row.appendChild(ktd)
                    var kink = this['description']
                    var pos = 1
                    $.each(group['columns'], function() {
                        var td = document.createElement('td')
                        td.classList.add('choiceCell')
                        var cdiv = document.createElement('div')
                        cdiv.classList.add('cdiv')
                        buildOptions(cdiv, kink, pos, index)
                        td.appendChild(cdiv)
                        row.appendChild(td)
                        pos += 1
                    })
                    index += 1
                    table.appendChild(row)
                })

                container.appendChild(title)
                container.appendChild(desc)
                container.appendChild(table)
                root.appendChild(container)

            })

        fill_cookie()
    }
    });


}

function fill_cookie(){
    var cdiv = document.getElementById('group_container');
    $.each(cdiv.childNodes, function(){
        $.each(this.childNodes, function(){
            if(this.tagName === 'TABLE'){
                $.each(this.childNodes, function(){
                    var first = true
                    var kink = "";
                    var pos = 0;
                    $.each(this.childNodes, function(){
                        if(this.tagName === 'TD'){

                            var div = this.childNodes[0].childNodes[0];

                            if(first){
                                first = false
                                $.each(this.parentNode.childNodes, function(){
                                    $.each(div.childNodes, function(){

                                            if(!(this.innerHTML === '')){
                                                if(this.tagName === 'LABEL' && this.className === 'kinkTitle'){
                                                    kink = this.innerText
                                                }

                                            }

                                    })
                                })
                            }



                            if(kink !== ""){

                                var cval = getCookieVal(kink, pos)
                                pos += 1;
                                if(cval !== '0' && this.className === 'choiceCell'){
                                    var cdiv = this.childNodes[0];
                                    if(cdiv.className === 'cdiv'){
                                        $.each(cdiv.childNodes, function(){
                                            if(this.value === cval){
                                                this.click()

                                            }
                                        })

                                    }

                                }

                            }






                        }
                    })
                })
            }
        })
    })
}

function submit_results(){
    var lc = window.localStorage
    var kinks = []
    var meta = []

    if(lc.getItem('meta_name') === null ||lc.getItem('meta_name') === ''){
        alert('Please enter a name or pseudonym!')
    } else if(lc.getItem('meta_name').length > 100) {
         alert('Name too long, max. 100 characters! Please reset your user')
    }else {
        $.each(window.groups, function(){
            $.each(this['rows'], function(){
                kinks.push({"id": this['id'], "val": lc.getItem(this['id'])})
            })
        })

        meta.push({"id": "name", "val": lc.getItem("meta_name")})
        meta.push({"id": "sex", "val": lc.getItem("meta_sex")})
        meta.push({"id": "age", "val": lc.getItem("meta_age")})
        meta.push({"id": "fap_freq", "val": lc.getItem("meta_fap_freq")})
        meta.push({"id": "sex_freq", "val": lc.getItem("meta_sex_freq")})
        meta.push({"id": "body_count", "val": lc.getItem("meta_body_count")})
        /*
        $.ajax({
            type: 'POST',
            url: "/",
            data: JSON.stringify({"meta": meta, "kinks": kinks}),
            success: function(response){
                console.log(response)
            },
            dataType: 'json',
            contentType: "application/json"
        })
        */

        fetch('/', {
            method: 'POST',
            headers: {'Content-Type': 'application/json'},
            body: JSON.stringify({"meta": meta, "kinks": kinks}),
        }).then(res => {
            window.location.href = '/results?token=' + $.cookie('token') + "&justCreated=true"
        })
    }
}


function togglePin(sender){
    var div = document.getElementById('c_container')
    if(div.classList.contains("pinned")){
        div.classList.remove("pinned")
        div.classList.add("rel")
    } else {
        div.classList.add("pinned")
        div.classList.remove("rel")
    }
}

//Collapsible
function buildCollapsibles(){
    var coll = document.getElementsByClassName("collapsible");
    var i;

    for (i = 0; i < coll.length; i++) {
      coll[i].addEventListener("click", function() {
        this.classList.toggle("active");
        var content = this.nextElementSibling;
        if (content.style.maxHeight){
          content.style.maxHeight = null;
        } else {
          content.style.maxHeight = content.scrollHeight + "px";
        }
      });
    }
}




function toggleFilter(event) {
    var src = event.srcElement;
    var current = document.getElementsByClassName("active")

    $.each(document.getElementsByClassName("filter"), function() {
        if(!(this === src)){
            this.classList.remove("active")
        }
    })

    if(current !== null){
        if(current[0] === src){
            src.classList.remove("active")
        } else {
            src.classList.add("active")
        }
    } else {
        src.classList.add("active")
    }

    var filterby = document.getElementsByClassName("active")

    $.each(document.getElementsByClassName("kink_row"), function() {
        this.classList.remove("hidden")
        if(!(filterby.length === 0)){
            if(!this.getAttribute("vals").includes(filterby[0].getAttribute("value"))){
                this.classList.add("hidden")
            }
        }
    })


    $.each(document.getElementsByClassName("kink_group"), function() {
        this.classList.remove("hidden")

        var rows_hidden = 0;
        var total_rows = 0;
        var children = this.children;
        for (var i = 0; i < children.length; i++) {
          var tc = children[i];
          if(tc.tagName === "DIV"){
            total_rows += 1;
            if(tc.classList.contains("hidden")){
                rows_hidden += 1;
            }
          }
        }

        if(rows_hidden === total_rows){
            this.classList.add("hidden")
        }
    })

}
