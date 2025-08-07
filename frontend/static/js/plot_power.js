const fileListUrl = '/api/files?source=plugs'; 
const apiUrl = '/api/data?date=recent&source=plugs';


// getAirtableData('https://communityvirtualpowerplant.com/api/gateway.php?table=events')


// function getAirtableData(url){
//   fetch(url)
//     .then(response => {
//       if (!response.ok) {
//         throw new Error('Network response was not OK');
//       }
//       return response.text(); // or response.text() if it's plain text
//     })
//     .then(data => {
//       const safeJSON = data.replace(/\bNaN\b/g, 'null');
//       data = JSON.parse(safeJSON);
//       //console.log('Data received:', data);
//       updateData(data);
//     })
//     .catch(error => {
//       console.error('There was a problem with the fetch:', error);
//     });
// }

function getColor(){
  // get colors between 20-240
  let r = (Math.floor(Math.random() * 200)+20).toString()
  let g = (Math.floor(Math.random() * 200)+20).toString()
  let b = (Math.floor(Math.random() * 200)+20).toString()
  let a = (1).toString();
  return `rgba(${r},${g},${b},${a})`
}

async function getFileList(){
  const response = await fetch(fileListUrl);
  files = await response.json()
  const sorted = files.sort((a, b) => a.localeCompare(b, undefined, { numeric: true }));
  
  myFiles= []
  for (let d = 5;d >0;d--){
    myFiles.push(sorted[sorted.length-d])
  }
  return myFiles
}

async function fetchAndPlotCSV(files) {
  try {
    const datetime = [];
    const cols = ['ac-W','batteryin-W','batteryout-W'];
    const y = {}
    const positionData = []
    cols.forEach(c=>{
          y[c] = []
        })

    files.forEach(f=>await {
      const response = await fetch(apiUrl);
      const csvText = await response.text();
      console.log(csvText)
      // Parse CSV manually
      const rows = csvText.trim().split('\n').map(row => row.split(','));
      const headers = rows.shift();
      
      // get column position for datetime
      let dti = headers.indexOf('datetime');

      rows.forEach(row => {
        datetime.push(row[dti]);
        positionData.push(row[headers.indexOf('position')])
        cols.forEach(c=>{
          // get col position
          let i = headers.indexOf(c); 
          let v = parseFloat(row[i])
          y[c].push(isNaN(v) ? null : v)
        })
        //y.push(parseFloat(row[1]));
      });
      
    })

    ///////////////////////////////////////////
    //********** BACKGROUND ******************/
    ///////////////////////////////////////////

    const shapes = []; // Will hold background color blocks
    const positions = ['normal','upcoming','ongoing'];

    const positionColors = []

    // randomly assign a unique color to each position
    positions.forEach(p=>{
      if (positionData.includes(p)){
        positionColors[p] = getColor()
      }
    })

    // console.log(positionColors)

    // Create background rectangles where mode changes
    let lastPosition = null;
    let startTime = null;

    // for (let i = 0; i < datetime.length; i++) {
    //   const currentPosition = positionData[i];
    //   const currentTime = datetime[i];
    //   if (currentPosition !== lastPosition) {
    //     if (lastPosition !== null) {
    //       // Close previous rectangle
    //       shapes.push({
    //         type: 'rect',
    //         xref: 'x',
    //         yref: 'paper',
    //         x0: startTime,
    //         x1: currentTime,
    //         y0: 0,
    //         y1: 1,
    //         fillcolor: positionColors[lastPosition],
    //         opacity: 0.3,
    //         line: { width: 0 }
    //       });
    //     }
    //     startTime = currentTime;
    //     lastPosition = currentPosition;
    //   }
    // }

    // // Add last rectangle
    // if (lastPosition !== null) {
    //   shapes.push({
    //     type: 'rect',
    //     xref: 'x',
    //     yref: 'paper',
    //     x0: startTime,
    //     x1: datetime[datetime.length - 1],
    //     y0: 0,
    //     y1: 1,
    //     fillcolor: positionColors[lastPosition],
    //     opacity: 0.3,
    //     line: { width: 0 }
    //   });
    // }

    // //dummy background traces
    // const backgroundLegendTraces = Object.entries(positionColors).map(([position, color], index) => ({
    //   name: `Position: ${position}`,
    //   type: 'scatter',
    //   mode: 'markers',     // don't plot points
    //   x: [datetime[0]], // Needs at least one point (we can use first datetime)
    //   y: [0], 
    //   hoverinfo: 'skip', // avoid hover distractions
    //   showlegend: true,
    //   marker: { 
    //     color: color,
    //     size: 8 // small marker, visible in legend
    //   },
    //   //legendgroup: 'positions'//, // optional: group legend items
    //   //line: { color } // ensures legend swatch gets the color
    //   legendgroup: 'positions',
    //   ...(index === 0 ? { 
    //     legendgrouptitle: { text: 'Positions' } 
    //   } : {})
    // }));


    ///////////////////////////////////////////
    //********** CREATE DATA TRACES***********/
    ///////////////////////////////////////////

    traces = []//...backgroundLegendTraces] // ... spreads content into array, so it isn't nested


    cols.forEach(c=>{
      t = {
        x: datetime,
        y: y[c],
        mode: 'lines+markers',
        type: 'scatter',
        name:c.replace('ac-W','AC (W)').replace('_',' ').replace('batteryin-W','Battery In (W)').replace('batteryout-W','Battery Out (W)')// make labels more readable
      }
      traces.push(t)
    })  


    //traces.push(...backgroundLegendTraces)

    Plotly.newPlot('plotPower',traces, {
      title: "Smart Plug Power Consumption",
      xaxis: { title: "Time" },
      yaxis: { title: "Power" },
      shapes: shapes,
      legend: {
        orientation: 'v',
        traceorder: 'grouped'
      }
    });
  } catch (error) {
    console.error('Error fetching or plotting CSV:', error);
  }
}

getFileList().then(res => {fetchAndPlotCSV(res)});