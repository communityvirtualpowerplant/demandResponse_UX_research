//let params = new URLSearchParams(document.location.search);
const performanceEndPt = '/api/performance';

getData('https://communityvirtualpowerplant.com/api/drux/gateway.php?table=events&key=12345')

function getData(url){
  fetch(url)
    .then(response => {
      if (!response.ok) {
        throw new Error('Network response was not OK');
      }
      return response.json(); // or response.text() if it's plain text
    })
    .then(data => {
      //const safeJSON = data.replace(/\bNaN\b/g, 'null');
      //data = JSON.parse(data);
      updateData(data['records']);
    })
    .catch(error => {
      console.error('There was a problem with the fetch:', error);
    });
}

function updateData(data){
    console.log(data)

    dates = []
    //datesStr = []
    data.forEach(e=>{
        //datesStr.push(e['fields']['date'])
        dateStrSplit = e['fields']['date'].split('/')
        dates.push(new Date(dateStrSplit[2], dateStrSplit[0] - 1, dateStrSplit[1],e['fields']['time']))
    })

    dates.sort((a, b) => a - b);

    const today = new Date();

    const filteredDates = dates.filter(date => {
      return date <= today;
    });

    const filteredDatesStr = []
    filteredDates.forEach(e=>{
        filteredDatesStr.push(String(e.getMonth()) + '/'+String(e.getDate())+'/'+String(e.getFullYear()));
    })

    console.log(dates)
    console.log(filteredDates)
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

let performance 
async function plotPerformance(dateStr){
    console.log(String(dateStr));

    try{
        const response = await fetch(performanceEndPt);
        performance = await response.json()
        console.log(performance)

        let eventData = performance[Object.keys(performance)[0]]
        // baselineLoad = eventData['baselineW']
        goal = eventData['goalPerc']
        eventLoad = eventData['loadW_hourly']
        flexLoad = eventData['flexW']

        // baselineLoadR = []
        // baselineLoad.forEach(g=>{
        //     baselineLoadR.push(String(Math.round(g*100)/100)+'W')
        // })
        flexLoadR = []
        flexLoad.forEach(g=>{
            flexLoadR.push(String(Math.round(g*100)/100)+'W')
        })

        eventLoadR = []
        eventLoad.forEach(g=>{
            eventLoadR.push(String(Math.round(g*100)/100)+'W')
        })

        perc = []
        goal.forEach(g=>{
            perc.push(String(Math.round(g*1000)/10)+'%')
        })

        hours = ['1 ('+perc[0]+')', '2 ('+perc[1]+')', '3 ('+perc[2]+')','4 ('+perc[3]+')']

        let trace1 = {
            x: hours,
            y: flexLoad,
            text: flexLoadR.map(String),
            textposition: 'auto',
            name: 'baseline load (W)',
            type: 'bar'
        };

        var trace2 = {
            x: hours,
            y: eventLoad,
            text: eventLoadR.map(String),
            textposition: 'auto',
            name: 'event load (W)',
            type: 'bar'
        };

        var data = [trace1, trace2];

        var layout = {barmode: 'stack',
            title: {text:"Event Performance (" + String(performance['flexW_avg']) + "W)"},
            xaxis: { title: "Hours" },
            yaxis: { title: "Load" }
        }

        Plotly.newPlot('plotEvent', data, layout);

    } catch (error) {
        console.error('Error fetching:', error);
    }
}


// // Control diagram interaction - Wait until DOM is ready
// document.addEventListener('DOMContentLoaded', () => {
//     const imgElement = document.getElementById('controlImage');

//     document.querySelectorAll('a[data-img]').forEach(link => {
//         link.addEventListener('click', event => {
//             event.preventDefault();
//             const filename = event.target.getAttribute('data-img');
//             imgElement.src = `${filename}`;
//         });
//     });
// });