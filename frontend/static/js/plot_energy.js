// get today's data
const apiUrl = '/api/data?file=recent';

function getColor(){
  // get colors between 50-245
  let r = (Math.floor(Math.random() * 195)+51).toString()
  let g = (Math.floor(Math.random() * 195)+51).toString()
  let b = (Math.floor(Math.random() * 195)+51).toString()
  let a = (.5).toString();
  return `rgba(${r},${g},${b},${a})`
}

async function fetchAndPlotCSV() {
  try {
    const response = await fetch(apiUrl);
    const csvText = await response.text();

    // Parse CSV manually
    const rows = csvText.trim().split('\n').map(row => row.split(','));
    const headers = rows.shift();

    // Assuming the first column is X (e.g., Date) and second column is Y (e.g., Value)
    const datetime = [];
    const cols = ['powerstation_percentage','powerstation_inputWAC','powerstation_inputWDC','powerstation_outputWAC','powerstation_outputWDC','relay1_power','relay2_power','relay3_power'];
    const y = {}
    const positionData = []


    cols.forEach(c=>{
          y[c] = []
        })

    rows.forEach(row => {
      datetime.push(row[0]);
      positionData.push(row[headers.indexOf('position')])
      cols.forEach(c=>{
        // get col position
        let i = headers.indexOf(c); 
        let v = parseFloat(row[i])
        y[c].push(isNaN(v) ? null : v)
      })
      //y.push(parseFloat(row[1]));
    });

    ///////////////////////////////////////////
    //********** BACKGROUND ******************/
    ///////////////////////////////////////////

    const shapes = []; // Will hold background color blocks
    const positions = ['A','B','C','D','E','F','G','EA','EB','EC','ED','EE','EF','EG','EH'];

    const positionColors = []

    // randomly assign a unique color to each position
    positions.forEach(p=>{
      if (positionData.includes(p)){
        positionColors[p] = getColor()
      }
    })

    console.log(positionColors)

    // Create background rectangles where mode changes
    let lastPosition = null;
    let startTime = null;

    for (let i = 0; i < datetime.length; i++) {
      const currentPosition = positionData[i];
      const currentTime = datetime[i];
      if (currentPosition !== lastPosition) {
        if (lastPosition !== null) {
          // Close previous rectangle
          shapes.push({
            type: 'rect',
            xref: 'x',
            yref: 'paper',
            x0: startTime,
            x1: currentTime,
            y0: 0,
            y1: 1,
            fillcolor: positionColors[lastPosition],
            opacity: 0.3,
            line: { width: 0 }
          });
        }
        startTime = currentTime;
        lastPosition = currentPosition;
      }
    }

    // Add last rectangle
    if (lastPosition !== null) {
      shapes.push({
        type: 'rect',
        xref: 'x',
        yref: 'paper',
        x0: startTime,
        x1: datetime[datetime.length - 1],
        y0: 0,
        y1: 1,
        fillcolor: positionColors[lastPosition],
        opacity: 0.3,
        line: { width: 0 }
      });
    }

    //dummy background traces
    const backgroundLegendTraces = Object.entries(positionColors).map(([position, color], index) => ({
      name: `Position: ${position}`,
      type: 'scatter',
      mode: 'markers',     // don't plot points
      x: [datetime[0]], // 👈 Needs at least one point (we can use first datetime)
      y: [0], 
      hoverinfo: 'skip', // avoid hover distractions
      showlegend: true,
      marker: { 
        color: color,
        size: 8 // small marker, visible in legend
      },
      //legendgroup: 'positions'//, // optional: group legend items
      //line: { color } // ensures legend swatch gets the color
      legendgroup: 'positions',
      ...(index === 0 ? { 
        legendgrouptitle: { text: 'Positions' } 
      } : {})
    }));


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
        name:c.replace('powerstation','battery').replace('_',' ').replace('percentage','%')// make labels more readable
      }

      traces.push(t)
    })  


    traces.push(...backgroundLegendTraces)

    Plotly.newPlot('plotEnergy',traces, {
      title: "Smart Power Station Data - Today",
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

fetchAndPlotCSV();