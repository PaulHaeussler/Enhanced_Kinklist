

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


}

function buildKink(id) {



}