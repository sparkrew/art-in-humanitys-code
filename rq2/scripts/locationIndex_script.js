const fs = require('fs-extra');
orderBy = require('lodash.orderby');

const repos_data = JSON.parse(fs.readFileSync('./final_deduplicated_all_repos_with_locations.json'));



var entries = [];

repos_data.forEach(r => {
    
    // get the location
    var place = r.main_contributor_profile.location_normalized

    var index = entries.findIndex(d => d.name == place)

    //if the current location is already in the index
    if (index != -1){
        entries[index].count ++

    }
    else {
        //else, create an index entry
        entries.push({
            name: place,
            count: 1,
            type: r.main_contributor_profile.location_type,
            country: r.main_contributor_profile.country,
            country_code: r.main_contributor_profile.country_code,
            lat: r.main_contributor_profile.location_lat,
            lon: r.main_contributor_profile.location_lon
        })
    }
    

})


var sorted = orderBy(entries, "count", "desc")
console.log("index size: ", sorted.length)

fs.writeJSONSync('./index_locations_deduplicated.json', sorted, {spaces: 2, encoding: 'utf8'});
//the resulting file is uploaded onto the noteebook: https://observablehq.com/@sparkrew/art-in-swh-rq2#index_locations_deduplicated