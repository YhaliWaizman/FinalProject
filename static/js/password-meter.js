$(document).ready(function() {
    $('#password').keyup(function() {
      var password = $('#password').val();
      var strength = calculate_password_strength(password);
      $('#strength').val(strength);
    });
  });
