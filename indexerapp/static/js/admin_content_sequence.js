// admin_content_sequence.js
/* (function($) {
    $(document).ready(function() {
        function updateSequenceInMs() {
            // Find the last row in the inline form
            var lastRow = $('#content_set-group .dynamic-content:last');

            // Find the input field for sequence_in_ms
            var sequenceInMsField = lastRow.find('[name$=sequence_in_ms]');

            if (sequenceInMsField.length > 0) {
                // Calculate the maximum value and increment
                var maxSequence = parseInt(lastRow.prev().find('[name$=sequence_in_ms]').val()) || 0;
                sequenceInMsField.val(maxSequence + 1);
            }
        }

        // Attach a click event to the "Add another Content" button
        $('#content_set-group .add-row a').on('click', updateSequenceInMs);

        // Initialize sequence_in_ms for existing rows
        $('#content_set-group .dynamic-content').each(updateSequenceInMs);
    });
})($); */