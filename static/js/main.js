// ─── SEAT SELECTION ─────────────────────────────────────────

function selectSeat(seatId, seatNumber) {
    // Remove previous selection
    document.querySelectorAll('.seat.selected').forEach(seat => {
        seat.classList.remove('selected');
        seat.classList.add('available');
    });

    // Mark new selection
    event.target.classList.remove('available');
    event.target.classList.add('selected');

    // Update summary
    document.getElementById('selected-seat-number').textContent = seatNumber;
    document.getElementById('selected-seat-id').value = seatId;
    document.getElementById('reservation-summary').style.display = 'block';
}