const endpoint = '/api/state';

async function fetchState(endpoint) {
  try {

    const response = await fetch(endpoint);
    state = await response.json()
    
    console.log(state)

    eventStatusContainer = window.getElementById('eventStatus')
    eventStatusContainer.text = 'test!'

  } catch (error) {
    console.error('Error fetching or plotting CSV:', error);
  }
}

fetchState(res);