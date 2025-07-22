let params = new URLSearchParams(document.location.search);
let name = 'home'//params.get("name"); update this to be dynamic

getData('https://communityvirtualpowerplant.com/api/gateway.php?table=live')
setInterval(getData,60000);


function getData(url){
  fetch(url)
    .then(response => {
      if (!response.ok) {
        throw new Error('Network response was not OK');
      }
      return response.text(); // or response.text() if it's plain text
    })
    .then(data => {
      const safeJSON = data.replace(/\bNaN\b/g, 'null');
      data = JSON.parse(safeJSON);
      //console.log('Data received:', data);
      updateData(data);
    })
    .catch(error => {
      console.error('There was a problem with the fetch:', error);
    });
}

function updateData(data){
    data = data['records']//[0]['fields']

    // Find index where name is
    const index = data.findIndex(item => item.fields.name === name);
    console.log(index); // Output: 1

    data = data[index]['fields']
    console.log(data)

    document.getElementById('mode').textContent = data['mode'];

    document.getElementById('position').textContent = data['position'];


    let eventStatus = '';
    if (data['event upcoming'] == 1){
        eventStatus = 'upcoming'
    } else if (data['event ongoing'] == 1){
        eventStatus = 'ongoing'
    }
    document.getElementById('eventStatus').textContent = eventStatus;
}


// Control diagram interaction - Wait until DOM is ready
document.addEventListener('DOMContentLoaded', () => {
    const imgElement = document.getElementById('controlImage');

    document.querySelectorAll('a[data-img]').forEach(link => {
        link.addEventListener('click', event => {
            event.preventDefault();
            const filename = event.target.getAttribute('data-img');
            imgElement.src = `${filename}`;
        });
    });
});