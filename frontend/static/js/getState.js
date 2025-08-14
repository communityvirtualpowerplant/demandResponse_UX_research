const endpoint = '/api/state';

async function fetchState(endpoint) {
  try {

    const response = await fetch(endpoint);
    state = await response.json()
    
    console.log(state)

    eStatus = 'No event'

    if (state['csrp']['now'] != false){
      eStatus = 'Event now!'
    }

    if (state['dlrp']['now'] != false ){
      eStatus = 'Event now!'//state['csrp']['upcoming'] 
    }

    if (state['csrp']['upcoming'] != false){
      eStatus = 'Upcoming at '+state['csrp']['upcoming'] 
    }

    if (state['dlrp']['upcoming'] != false){
      eStatus = 'Upcoming at '+ state['dlrp']['upcoming'] 
    }

    eventStatusContainer = document.getElementById('eventStatus')
    eventStatusContainer.innerHTML = eStatus
        
    let eventValueCSRP = document.getElementById('csrpAvgGoal')
    let cG = state['csrp']['goalAvg'] * 100
    eventValueCSRP.innerHTML  = cG

    let eventValueDLRP = document.getElementById('dlrpAvgGoal')
    let dG = state['dlrp']['goalAvg'] * 100
    eventValueDLRP.innerHTML  = dG

    // check if events have occurred
    let eC = 0
    if (dG = state['csrp']['count']){
      eC = eC + 1
    }
    if (dG = state['dlrp']['count']){
      eC = eC + 1
    }
    if (eC > 0){
      eventValueTot = document.getElementById('totAvgGoal')
      eventValueTot.innerHTML  = (cG + dG)/eC
    }

  } catch (error) {
    console.error('Error fetching or showing state:', error);
  }
}

fetchState(endpoint);