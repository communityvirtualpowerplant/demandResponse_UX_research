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

  } catch (error) {
    console.error('Error fetching or showing state:', error);
  }
}

fetchState(endpoint);