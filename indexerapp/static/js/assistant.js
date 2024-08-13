assistant_init = function()
{
    console.log('assistant');

}



function askQuestion() {
    var questionInput = document.getElementById('question');
    var question = questionInput.value;

    if (question.trim() === '') {
        alert('Please enter a question.');
        return;
    }

    var loader = document.getElementById('loader');
    var answerDiv = document.getElementById('answer');

    loader.style.display = 'block';
    answerDiv.innerHTML = '';

    $.ajax({
        type: 'GET',
        url: '/assistant/?q=' + question,
        success: function (data) {
            loader.style.display = 'none';
            displayAnswer(data);
        },
        error: function () {
            loader.style.display = 'none';
            alert('Error fetching data.');
        }
    });
}

function displayAnswer(data) {
    var answerDiv = document.getElementById('answer');

    if (Array.isArray(data.info) && data.info.length > 0 && typeof data.info[0] === 'object') {
        var keys = Object.keys(data.info[0]);
        var table = '<h2>Answer:</h2><table id="dataTable"><thead><tr>';

        keys.forEach(function (key) {
            table += '<th>' + key + '</th>';
        });

        table += '</tr></thead><tbody>';

        data.info.forEach(function (item) {
            table += '<tr>';
            keys.forEach(function (key) {
                table += '<td>' + item[key] + '</td>';
            });
            table += '</tr>';
        });

        table += '</tbody></table>';
        answerDiv.innerHTML = table;

        // Convert table to DataTable
        $('#dataTable').DataTable();
    } else if (Array.isArray(data.info) && data.info.length === 1 && typeof data.info[0] === 'object') {
        // Handle single-row data
        var singleRowData = data.info[0];
        var singleRowKeys = Object.keys(singleRowData);
        answerDiv.innerHTML = '<h2>Answer:</h2><table id="dataTable"><thead><tr><th>' + singleRowKeys[0] + '</th></tr></thead><tbody><tr><td>' + singleRowData[singleRowKeys[0]] + '</td></tr></tbody></table>';

        // Convert table to DataTable
        $('#dataTable').DataTable();
    } else if (typeof data.info === 'number') {
        answerDiv.innerHTML = '<h2>Answer:</h2><p>' + data.info + '</p>';
    } else {
        answerDiv.innerHTML = '<h2>Answer:</h2><p>No data available</p>';
    }
}

