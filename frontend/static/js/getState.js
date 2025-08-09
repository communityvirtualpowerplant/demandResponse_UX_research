const endpoint = '/api/state';

async function fetchState(endpoint) {
  try {

    const response = await fetch(endpoint);
    state = await response.json()
    
    console.log(state)

    eventStatusContainer = document.getElementById('eventStatus')
    eventStatusContainer.innerHTML = 'test!'

  } catch (error) {
    console.error('Error fetching or showing state:', error);
  }
}

fetchState(endpoint);