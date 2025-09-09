

startKinkId = 1001;


// Add the helper function at the top of mobile.js
function getKinkCounts() {
    let total_kinks = 0;
    let entered_kinks = 0;
    let total_fields = 0;
    let entered_fields = 0;
    let meta_count = 0;
    let meta_entered = 0;

    for (let key in localStorage) {
        if (localStorage.hasOwnProperty(key)) {
            if (key.startsWith('meta_')) {
                meta_count++;
                const value = localStorage.getItem(key);
                if (value && value !== '' && value !== 'null') {
                    meta_entered++;
                }
            } else if (!isNaN(parseInt(key))) {
                total_kinks++;
                try {
                    const vals = JSON.parse(localStorage.getItem(key));
                    if (Array.isArray(vals)) {
                        total_fields += vals.length;
                        let hasEntry = false;
                        for (let val of vals) {
                            if (val !== "0" && val !== 0) {
                                entered_fields++;
                                hasEntry = true;
                            }
                        }
                        if (hasEntry) {
                            entered_kinks++;
                        }
                    }
                } catch(e) {
                    console.error('Error parsing kink data for key:', key);
                }
            }
        }
    }

    return {
        total_kinks: total_kinks,
        entered_kinks: entered_kinks,
        total_fields: total_fields,
        entered_fields: entered_fields,
        completion_rate: total_fields > 0 ? Math.round((entered_fields / total_fields) * 100) : 0,
        meta_count: meta_count,
        meta_entered: meta_entered
    };
}

// Enhanced mobile submit function
function mobile_submit(){
    try {
        var lc = window.localStorage;
        var kinks = [];
        var meta = [];

        // Get detailed counts for logging
        const counts = getKinkCounts();

        getProgress();

        // Log submission attempt
        fetch('/log_client_error', {
            method: 'POST',
            headers: {'Content-Type': 'application/json'},
            body: JSON.stringify({
                message: 'Mobile submission attempt',
                event_type: 'MOBILE_SUBMIT_ATTEMPT',
                kink_stats: counts,
                localStorage_size: JSON.stringify(localStorage).length,
                url: window.location.href,
                timestamp: new Date().toISOString(),
                user_agent: navigator.userAgent,
                fields_filled: window.fields_filled,
                total_fields: window.total_fields
            })
        });

        // Critical check: Are we about to submit empty data?
        if (counts.entered_fields === 0) {
            fetch('/log_client_error', {
                method: 'POST',
                headers: {'Content-Type': 'application/json'},
                body: JSON.stringify({
                    message: 'CRITICAL: Mobile attempting to submit with zero entered fields',
                    event_type: 'MOBILE_EMPTY_SUBMIT_ATTEMPT',
                    kink_stats: counts,
                    localStorage_keys: Object.keys(localStorage),
                    timestamp: new Date().toISOString(),
                    user_agent: navigator.userAgent
                })
            });

            alert('No data to submit. Please fill out the questionnaire.');
            return;
        }

        // Your existing validation
        if(window.fields_filled - window.total_fields !== 0){
            if(!confirm("It seems you missed " + (window.total_fields - window.fields_filled) + " Questions, are you sure you want to submit your results? Click Cancel to go back")){
                window.location.href = '/jump';
                return;
            }
        }

        // Validate meta_name
        if(lc.getItem('meta_name') === null || lc.getItem('meta_name') === ''){
            fetch('/log_client_error', {
                method: 'POST',
                headers: {'Content-Type': 'application/json'},
                body: JSON.stringify({
                    message: 'Mobile submit missing meta_name',
                    event_type: 'MOBILE_MISSING_META',
                    kink_stats: counts,
                    timestamp: new Date().toISOString()
                })
            });
            window.location.href = '/meta?err=1';
            return;
        } else if(lc.getItem('meta_name').length > 100) {
            window.location.href = '/meta?err=1';
            return;
        }

        // Collect data with error handling
        let parseErrors = 0;
        $.each(Object.keys(lc), function(){
            try {
                val = lc.getItem(this);
                if(this.startsWith('meta_')){
                    meta.push({"id": this.valueOf().substring(5), "val": val});
                } else if (!isNaN(parseInt(this))) {
                    // Additional validation for mobile
                    const kinkId = parseInt(String(this));
                    if (kinkId > 0) {  // Sanity check
                        kinks.push({"id": kinkId, "val": val});
                    }
                }
            } catch(e) {
                parseErrors++;
                console.error('Error processing key:', this, e);
            }
        });

        // Log if there were parsing errors
        if (parseErrors > 0) {
            fetch('/log_client_error', {
                method: 'POST',
                headers: {'Content-Type': 'application/json'},
                body: JSON.stringify({
                    message: `Mobile submit had ${parseErrors} parsing errors`,
                    event_type: 'MOBILE_PARSE_ERRORS',
                    kink_stats: counts,
                    timestamp: new Date().toISOString()
                })
            });
        }

        // Critical check: Do we have kinks array?
        if (kinks.length === 0) {
            fetch('/log_client_error', {
                method: 'POST',
                headers: {'Content-Type': 'application/json'},
                body: JSON.stringify({
                    message: 'CRITICAL: Mobile has no kinks array after processing',
                    event_type: 'MOBILE_NO_KINKS_PROCESSED',
                    kink_stats: counts,
                    localStorage_keys: Object.keys(localStorage).slice(0, 20), // First 20 keys for debugging
                    meta_collected: meta.length,
                    timestamp: new Date().toISOString(),
                    user_agent: navigator.userAgent
                })
            });
            alert('Error processing data. Please try again or use desktop version.');
            return;
        }

        // Log pre-submission state
        fetch('/log_client_error', {
            method: 'POST',
            headers: {'Content-Type': 'application/json'},
            body: JSON.stringify({
                message: 'Mobile pre-submission state',
                event_type: 'MOBILE_PRE_SUBMIT',
                kinks_count: kinks.length,
                meta_count: meta.length,
                kink_stats: counts,
                timestamp: new Date().toISOString()
            })
        });

        // Submit with error handling
        fetch('/', {
            method: 'POST',
            headers: {'Content-Type': 'application/json'},
            body: JSON.stringify({"meta": meta, "kinks": kinks}),
        }).then(res => {
            if (!res.ok) {
                throw new Error(`Submit failed with status: ${res.status}`);
            }

            // Log successful submission
            fetch('/log_client_error', {
                method: 'POST',
                headers: {'Content-Type': 'application/json'},
                body: JSON.stringify({
                    message: 'Mobile submission successful',
                    event_type: 'MOBILE_SUBMIT_SUCCESS',
                    kink_stats: counts,
                    timestamp: new Date().toISOString()
                })
            });

            // Check if token cookie was set
            const token = $.cookie('token');
            if (!token) {
                throw new Error('No token received from server');
            }

            window.location.href = '/results?token=' + token + "&justCreated=true";
        }).catch(err => {
            // Log submission failure with details
            fetch('/log_client_error', {
                method: 'POST',
                headers: {'Content-Type': 'application/json'},
                body: JSON.stringify({
                    message: 'Mobile submit failed',
                    event_type: 'MOBILE_SUBMIT_FAILURE',
                    error: err.toString(),
                    kink_stats: counts,
                    kinks_attempted: kinks.length,
                    meta_attempted: meta.length,
                    timestamp: new Date().toISOString(),
                    user_agent: navigator.userAgent
                })
            });

            alert('Submission failed. Please check your connection and try again.');
            console.error('Submit error:', err);
        });

    } catch(e) {
        // Catch-all for any unexpected errors
        try {
            const counts = getKinkCounts();
            fetch('/log_client_error', {
                method: 'POST',
                headers: {'Content-Type': 'application/json'},
                body: JSON.stringify({
                    message: 'Mobile submit function critical error',
                    event_type: 'MOBILE_SUBMIT_CRITICAL_ERROR',
                    error: e.toString(),
                    stack: e.stack,
                    kink_stats: counts || {},
                    timestamp: new Date().toISOString(),
                    user_agent: navigator.userAgent,
                    localStorage_accessible: typeof localStorage !== 'undefined'
                })
            });
        } catch(logErr) {
            console.error('Failed to log critical error:', logErr);
        }

        alert('An error occurred during submission. Please try again or use the desktop version.');
        console.error('Submit critical error:', e);
    }
}

// Also add a mobile-specific health check
function mobileHealthCheck() {
    try {
        const counts = getKinkCounts();

        // Check for concerning states
        if (window.total_fields && window.fields_filled !== undefined) {
            // Check if the window variables match localStorage
            if (Math.abs(counts.entered_fields - window.fields_filled) > 5) {
                fetch('/log_client_error', {
                    method: 'POST',
                    headers: {'Content-Type': 'application/json'},
                    body: JSON.stringify({
                        message: 'Mobile state mismatch detected',
                        event_type: 'MOBILE_STATE_MISMATCH',
                        window_fields_filled: window.fields_filled,
                        window_total_fields: window.total_fields,
                        actual_entered: counts.entered_fields,
                        actual_total: counts.total_fields,
                        timestamp: new Date().toISOString()
                    })
                });
            }
        }
    } catch(e) {
        console.error('Health check error:', e);
    }
}

// Run health check periodically on mobile
if (typeof setInterval !== 'undefined') {
    setInterval(mobileHealthCheck, 45000); // Every 45 seconds on mobile
}

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
    updateProgressM();
}

function updateProgressM() {
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



function enterChoiceM(sender){
    var parent = sender.parentNode;
    var val = sender.value;
    var id = parseInt(document.getElementById("kinkID").innerText);
    window.fields_filled += 1;
    updateProgressM();
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

function removeChoiceM(sender){
    var parent = sender.parentNode;
    var val = sender.value;
    var id = parseInt(document.getElementById("kinkID").innerText);
    window.fields_filled -= 1;
    updateProgressM();
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

function buildJumpProgress(){
    $.each(document.getElementsByClassName('li_kink'), function() {
        var id = this.getAttribute("id")
        var vals = JSON.parse(window.localStorage.getItem(parseInt(id)))
        var pstr = "["
        var done = "✅"
        var not_done = " "
        for(var i = 0; i < vals.length; i++){
            var tmp = ""
            if(vals[i] === "0"){
                tmp = not_done
            } else {
                tmp = done
            }

            if(i === vals.length - 1){
                pstr += tmp + "] "
            } else {
                pstr += tmp + " | "
            }
        }
        this.innerText = pstr + this.innerText;

    })

}

function buildFeedbackBtn(){

            var coll = document.createElement('button')
            coll.id = 'missingKinkColl'
            coll.innerText = 'Feedback / My Kink is missing :('
            coll.classList.add('collapsible')
            var content = document.createElement('div')
            content.classList.add('content')
            var sp = document.createElement('span')
            sp.innerText = "Please enter and describe the missing kink, ideally including a fitting category and image, or just provide some feedback:"
            var ta = document.createElement('textarea')
            ta.classList.add('ta')
            ta.id = 'missingKink'
            ta.maxLength = 2000
            content.appendChild(sp)
            content.appendChild(ta)
            var send = document.createElement('btn')
            send.id = 'missingKinkSubmit'
            send.classList.add('submit')
            send.style.width = '90%'
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
            document.getElementById('feedback').appendChild(coll)
            document.getElementById('feedback').appendChild(content)
            buildCollapsibles()


}