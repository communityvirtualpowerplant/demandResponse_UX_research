//let params = new URLSearchParams(document.location.search);
const performanceEndPt = '/api/performance';

const startDateStr = "2025-08-12"; // YYYY-MM-DD format
const startDate = new Date(startDateStr);

//getData('https://communityvirtualpowerplant.com/api/drux/gateway.php?table=events&key=12345')

// function getData(url){
//   fetch(url)
//     .then(response => {
//       if (!response.ok) {
//         throw new Error('Network response was not OK');
//       }
//       return response.json(); // or response.text() if it's plain text
//     })
//     .then(data => {
//       //const safeJSON = data.replace(/\bNaN\b/g, 'null');
//       //data = JSON.parse(data);
//       updateData(data['records']);
//     })
//     .catch(error => {
//       console.error('There was a problem with the fetch:', error);
//     });
// }

let performanceData = {}

document.addEventListener('DOMContentLoaded', () => {
  init().catch(err => console.error(err));
});

async function init() {
  performanceData = await getPerformance();
  makeDateLinks(performanceData);
}

function formationTime(dt){
    const isoNoTZ = 
    dt.getFullYear() + '-' +
    String(dt.getMonth() + 1).padStart(2, '0') + '-' +
    String(dt.getDate()).padStart(2, '0') + 'T' +
    String(dt.getHours()).padStart(2, '0') + ':' +
    String(dt.getMinutes()).padStart(2, '0') + ':' +
    String(dt.getSeconds()).padStart(2, '0');

  return isoNoTZ
}
async function getPerformance (){
    try{
        const response = await fetch(performanceEndPt);
        perf = await response.json()
        return perf;
    } catch (error) {
        console.error('Error fetching:', error);
        return {}
    }
}

async function makeDateLinks(perf){  
        datesC = []
        datesD=[]
        //datesStr = []
        Object.keys(perf).forEach(e=>{
            //datesStr.push(e['fields']['date'])
            console.log(e)
            //dateStrSplit = e.split('T')[0].split('-')
            if (perf[e]['event']=='csrp'){
                datesC.push(new Date(e))
            } else {
                datesD.push(new Date(e))
            }
        })
        //console.log(dates)
        datesC.sort((a, b) => a - b);
        datesD.sort((a, b) => a - b);

        //filter out entries prior to August 10th
        const filteredDatesC = datesC.filter(date => {
          return date >= startDate;
        });
        //console.log(filteredDatesC)

        const filteredDatesD = datesD.filter(date => {
          return date >= startDate;
        });
        //console.log(filteredDatesD)

        //format datetime strings
        const filteredDatesStrC = []
        filteredDatesC.forEach(e=>{
            filteredDatesStrC.push(formationTime(e));//.toISOString());
        })

        const filteredDatesStrD = []
        filteredDatesD.forEach(e=>{
            filteredDatesStrD.push(formationTime(e));//.toISOString());
        })

        let cValue = 0
        let dValue = 0

        filteredDatesStrC.forEach(e=>{
            cValue = cValue + perf[e]['flexW_avg']
        })

        filteredDatesStrD.forEach(e=>{
            dValue = dValue + perf[e]['flexW_avg']
        })

        perfValuekW = 18
        cValue = perfValuekW*(cValue*0.001)/filteredDatesStrC.length
        dValue = perfValuekW*(dValue*0.001)/filteredDatesStrD.length
        
        //replace NaN
        if (!Number.isFinite(cValue)){
            cValue = 0;
        }

        //replace NaN
        if (!Number.isFinite(dValue)){
            dValue = 0;
        }

        let totValue = cValue + dValue

        console.log('csrp:')
        console.log(filteredDatesStrC)
        console.log(cValue)

        console.log('dlrp:')
        console.log(filteredDatesStrD)
        console.log(dValue)

        eventValueCSRP = document.getElementById('csrpValue')
        eventValueCSRP.innerHTML  = Math.round(cValue*100)/100

        eventValueDLRP = document.getElementById('dlrpValue')
        eventValueDLRP.innerHTML  = Math.round(dValue*100)/100

        eventValueTot = document.getElementById('totValue')
        eventValueTot.innerHTML  = Math.round((cValue+dValue)*100)/100

        eventDateCSRP = document.getElementById('eventDatesCSRP')
        eventDateCSRP.innerHTML  = ''
        if (filteredDatesStrC.length ==0){
            eventDateCSRP.innerHTML  = 'No events yet'
        }
        

        eventDateDLRP = document.getElementById('eventDatesDLRP')
        eventDateDLRP.innerHTML  = ''
        if (filteredDatesStrD.length ==0){
            eventDateDLRP.innerHTML  = 'No events yet'
        }

        filteredDatesStrC.forEach(d=>{
            let a = document.createElement('a');
            let link = document.createTextNode(d);
            // Append the text node to anchor element.
            a.appendChild(link);
            a.href = "#"; 
            a.classList.add('perfLink');
            a.classList.add('inactive-link');
            a.addEventListener('click', function (e) {
                e.preventDefault(); // Prevent the # from scrolling
                plotPerformance(d, this);
                });
            // Set the href property.
            //a.href = "javascript:plotPerformance('"+d+"')";
            // Append the anchor element to the body.
            eventDateCSRP.appendChild(a);
        })

        filteredDatesStrD.forEach(d=>{
            let a = document.createElement('a');
            let link = document.createTextNode(d);
            // Append the text node to anchor element.
            a.appendChild(link);
            // Set the href property.
            //a.href = "javascript:plotPerformance('"+d+"',this)";
            // Append the anchor element to the body.
            a.href = "#"; 
            a.classList.add('perfLink');
            a.classList.add('inactive-link');
            a.addEventListener('click', function (e) {
                e.preventDefault(); // Prevent the # from scrolling
                plotPerformance(d, this);
                });
            eventDateDLRP.appendChild(a);
        })
}

async function plotPerformance(date,ahref){

    if (ahref === undefined) {
        console.log('ahref undefined');
    } else {    
        // remove the highlighted class link
        document.querySelectorAll('.perfLink').forEach(link => {
            link.classList.remove('active-link');
            link.classList.add('inactive-link');
          });

        // Make the clicked link active
        ahref.classList.remove('inactive-link');
        ahref.classList.add('active-link');
    }
    
    try{
        let myKey
        Object.keys(performanceData).forEach(e=>{
            console.log(e)
            if (e == date){
                myKey =e
            }
        })

        let eventData = performanceData[myKey]
        console.log(eventData)
        baselineLoad = eventData['baselineW']
        goal = eventData['goalPerc']
        eventLoad = eventData['loadW_hourly']
        //flexLoad = eventData['flexW']

        baselineLoadR = []
        baselineLoad.forEach(g=>{
            baselineLoadR.push(String(Math.round(g*100)/100)+'W')
        })

        // flexLoadR = []
        // flexLoad.forEach(g=>{
        //     flexLoadR.push(String(Math.round(g*100)/100)+'W')
        // })

        eventLoadR = []
        eventLoad.forEach(g=>{
            if (g != -1){
                eventLoadR.push(String(Math.round(g*100)/100)+'W')
            } else {
                eventLoadR.push('NaN')
            }
        })

        perc = []
        goal.forEach(g=>{
            perc.push(String(Math.round(g*1000)/10)+'%')
        })

        hours = ['1 ('+perc[0]+')', '2 ('+perc[1]+')', '3 ('+perc[2]+')','4 ('+perc[3]+')']

        let trace1E = {
            x: hours,
            y: baselineLoad,
            text: baselineLoadR.map(String),
            textposition: 'auto',
            name: 'Baseline Load (W)',
            type: 'bar'
        };

        var trace2E = {
            x: hours,
            y: eventLoad,
            text: eventLoadR.map(String),
            textposition: 'auto',
            name: 'Event Load (W)',
            type: 'bar'
        };

        var dataE = [trace1E, trace2E];

        var layoutE = {barmode: 'group',
            title: {text: date + " Event Performance by Hour (Avg Flex: " + String(Math.round(eventData['flexW_avg']*100)/100) + "W)"},
            xaxis: { title: "Hours" },
            yaxis: { title: "Load" }
        }

        Plotly.newPlot('plotEvent', dataE, layoutE);

    } catch (error) {
        console.error('Error fetching:', error);
    }
}