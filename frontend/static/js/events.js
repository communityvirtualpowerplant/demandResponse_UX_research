//let params = new URLSearchParams(document.location.search);
const performanceEndPt = '/api/performance';

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
        dates = []
        //datesStr = []
        Object.keys(perf).forEach(e=>{
            //datesStr.push(e['fields']['date'])
            console.log(e)
            //dateStrSplit = e.split('T')[0].split('-')
            dates.push(new Date(e))//new Date(dateStrSplit[0], dateStrSplit[1] - 1, dateStrSplit[2],e.split('T')[1].split(':')[0]))
        })
        //console.log(dates)
        dates.sort((a, b) => a - b);

        //const today = new Date();
        // const filteredDates = dates.filter(date => {
        //   return date <= today;
        // });

        const filteredDatesStr = []
        dates.forEach(e=>{
            filteredDatesStr.push(e.toISOString())//String(e.getMonth()+1) + '/'+String(e.getDate())+'/'+String(e.getFullYear()));
        })

        console.log(dates)
        console.log(filteredDatesStr)

        eventDateContainer = document.getElementById('eventDates')
        eventDateContainer.innerHTML  = ''

        filteredDatesStr.forEach(d=>{
            let a = document.createElement('a');
            let link = document.createTextNode(d);
            // Append the text node to anchor element.
            a.appendChild(link);
            // Set the href property.
            a.href = "javascript:plotPerformance('"+d+"')";
            // Append the anchor element to the body.
            eventDateContainer.appendChild(a);
        })
}

async function plotPerformance(date){
    
    try{
        // const response = await fetch(performanceEndPt);
        // performance = await response.json()
        // console.log(performance)

        let myKey
        Object.keys(performanceData).forEach(e=>{
            console.log(e)
            //e.split('T')[0].split('-')
            //kStr = String(e.getMonth()) + '/'+String(e.getDate())+'/'+String(e.getFullYear())
            if (e == date.replace('.00Z','')){
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
            eventLoadR.push(String(Math.round(g*100)/100)+'W')
        })

        perc = []
        goal.forEach(g=>{
            perc.push(String(Math.round(g*1000)/10)+'%')
        })

        hours = ['1 ('+perc[0]+')', '2 ('+perc[1]+')', '3 ('+perc[2]+')','4 ('+perc[3]+')']

        let trace1E = {
            x: hours,
            y: baselineLoadR,
            text: baselineLoadR.map(String),
            textposition: 'auto',
            name: 'Baseline Load (W)',
            type: 'bar'
        };

        var trace2E = {
            x: hours,
            y: eventLoadR,
            text: eventLoadR.map(String),
            textposition: 'auto',
            name: 'Event Load (W)',
            type: 'bar'
        };

        var dataE = [trace1E, trace2E];

        var layoutE = {barmode: 'group',
            title: {text:"Event Performance (" + String(performance['flexW_avg']) + "W)"},
            xaxis: { title: "Hours" },
            yaxis: { title: "Load" }
        }

        Plotly.newPlot('plotEvent', dataE, layoutE);

    } catch (error) {
        console.error('Error fetching:', error);
    }
}